#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
author: Ox25
date: 12/04/2021
version : 2.0
description: Srap email from URLs
"""

import argparse
from multiprocessing import Pool
import requests
from bs4 import BeautifulSoup
import urllib.parse as urlparse
import os, sys, re
import socket
import validators

import time, random


def load_file(file):
  ''' read file line by line and output a list'''
  if os.path.isfile(file):
    with open(file) as f:
      lines = f.read().splitlines()
    return lines
  else:
    print(f"\033[0;31mERROR: file not exist [{file}]\033[0m")
    sys.exit(1)


def check_url_format(url):
  ''' valide or reformat URL format. URL must start with http(s)'''
  
  if url.find('http') != 0:
    url = 'http://' + url

  if validators.url(url) is True:
    return url
  else:
    return False


def scrape_urls(site, blacklist, max_depth = 1, cur_depth=0, urls=[],emails=[]):
  ''' recursive function to grep url from url'''
  pid = os.getpid()  
  url = urlparse.urlparse(site)
  status_code = None
  base_url = url.scheme + '://' + url.netloc
  if url.path != '':
    base_url = base_url + os.path.dirname(url.path) + '/' # do // sometime
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
  try:
    r = requests.get(site,  headers=headers)
    status_code = r.status_code
  except:
    print(f"  WARNING: [{pid}] request fail {site}")
    return {'urls': urls, 'emails': emails} # maybe ...

  print(f"  INFO: [{pid}] HTTP status code [{status_code}]")
  s = BeautifulSoup(r.text,"html.parser")
  mails = scrap_email(r.text)

  for mail in mails:
    if mail not in emails:
      emails.append(mail)

  nb_emails = len(emails)
  print(f"  Info: pid[{pid}] depth[{cur_depth}] emails[{nb_emails}] {site}")

  if cur_depth >= max_depth: # exit: to mutch iterration
    print(f"  INFO: pid[{pid}] max depth {cur_depth} {max_depth}")
    return {'urls': urls, 'emails': emails}

  for a in s.find_all("a", href=True):
    site = format_url(a['href'],base_url)
    if site is not False:
      if site not in  urls and check_extension(site, blacklist):
        urls.append(site)
        time.sleep(random.randint(1,4)/5) # no dos
        scrape_urls(site, blacklist, max_depth, cur_depth+1, urls, emails)

  return {'urls': urls, 'emails': emails}


def format_url(url_tmp,url_valide):
  ''' create Url and check if in domain. need http predix for url_valide'''
  url_temp_raw = url_tmp
  url_valide_raw = url_valide

  url_tmp = urlparse.urlparse(url_tmp)
  url_valide = urlparse.urlparse(url_valide)

  if url_tmp.netloc == '' or url_tmp.netloc == url_valide.netloc:
    if url_tmp.path != '' and url_tmp.path.find('(') == -1 and url_tmp.scheme != 'mailto':

      url_join = urlparse.urljoin(url_valide_raw, url_temp_raw)
      return url_join

  return False


def check_redirection(url, max_redirection=5):
  ''' check if url is redirect and return value'''
  count = 0
  while count < max_redirection:
    count = count + 1
    try:
      req = requests.head(url, timeout=(2, 5), allow_redirects=False)
    except:
      print("\033[0;31mWARNING: check_redirection error (SSL/Timeout ...)\033[0m")
      return False

    if 'location' in req.headers:
      url = req.headers['location']
      if count == max_redirection:
        print("\033[0;31mWARNING: To mutch redirection\033[0m")
        return False
    else:
      break

  return url


def valid_domain(url):
  ''' ns lookup to resolv domain to IP'''

  url = urlparse.urlparse(url)
  domain = url.netloc
  try:
    s = socket.getaddrinfo(domain,0,2,0,0)
    return True
  except:
    print("\033[0;31mWARNING: domain resolution fail\033[0m")
    return False


def scrap_email(txt):
  ''' scrap mail on txt'''
  out = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?!png|jpg|gif)[A-Z|a-z]{2,}\b", txt, re.I)
  return out


def write_to(file,values):
  ''' Write list to file line by line'''
  if isinstance(values, list):
    try:
      f = open(file, "w")
      for value in values:
        f.write(f"{value}\n")
      f.close()
      return True
    except:
      print("\033[0;31mWARNING: Fail to write file\033[0m")
      return False
  else:
    print('\033[0;31mWARNING: Need a list, wrong type\033[0m')
    return False

def check_extension(url,blacklist=[]):
  ''' check if extension is in blacklist. need http prefix'''
  path = urlparse.urlparse(url).path
  if os.path.splitext(path)[1]:
    if os.path.splitext(path)[1] in blacklist:
      return False
    else:
      return True
  else:
    return True # no extension


def scrap(datas):
  ''' scrap url '''
  pid = os.getpid()

  url = datas['url']
  folder = datas['out']
  blacklist = datas['blacklist']
  max_depth = datas['max_depth']

  print(f"\033[0;32mINFO [{pid}] Start {url}\033[0m")

  check_url = check_url_format(url)
  if check_url is False:
    print(f"\033[0;31mWARNING: [{pid}] invalid URL [{url}]\033[0m")
  else:
    if valid_domain(check_url):
      rurl = check_redirection(check_url)
      if rurl is not False:
        if check_url not in rurl:
          print(f"\033[0;32mINFO [{pid}] reddirection {check_url} > {rurl}\033[0m")
        else:
          print(f"\033[0;32mINFO [{pid}] Scrap {rurl}\033[0m")

        file = urlparse.urlparse(rurl).hostname + '.txt'
        path = os.path.join(folder,file)
        
        if os.path.isfile(path) is False:
          #scrap Url
          result = scrape_urls(rurl,blacklist,max_depth,0,[],[])
          mails = result['emails']
          # write emails in file
          write_to(path,mails)
        else:
          print(f"\033[0;32mINFO [{pid}] File already exist {path}")
      else:
        print(f"\033[0;31mWARNING: [{pid}] request error {check_url}\033[0m")
    else:
      print(f"\033[0;31mWARNING: [{pid}] name resolution error {check_url}\033[0m")
  
  print(f'\033[0;32mINFO: [{pid}] END {check_url}\033[0m')


def main():
  """ main code """

  threads = 4
  file = 'scrabe.txt'
  folder = 'out'
  blacklist = ['.pdf','.xls','.xlsx','.pptx','.doc','.docx','.docm','.jpg','.jpeg','.png','.gif','.tiff']
  max_depth = 1
  description = 'Scrap email from URLs'

  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('-t','--threads', type=int, default=threads, help='number of default concurent threads')
  parser.add_argument('-f','--file', default=file, help='file with a URL line by line. Best to prefix URL with http/https (default scrabe.txt)')
  parser.add_argument('-o','--out', default=folder, help='folder to save output (default /out')
  parser.add_argument('-m','--max', default=max_depth, help='set recurisve depth (default 1') 
  args = parser.parse_args()

  threads = args.threads
  file = args.file
  folder = args.out
  max_depth = int(args.max)

  urls = load_file(file)
  print(f"\033[0;32mINFO: Load {len(urls)} from {file}\033[0m")
  print(f"\033[0;32mINFO: Extension blacklist: {blacklist}\033[0m")

  if not os.path.exists(folder):
    os.mkdir(folder)

  # deduplicate
  urls = list(set(urls))

  jobs = []

  for url in urls:
    jobs.append({'out':folder, 'url':url, 'blacklist': blacklist, 'max_depth': max_depth})

  p = Pool(threads)
  p.map(scrap,jobs)
  p.close()
  p.join()


# main
if __name__ == '__main__':
        main()






