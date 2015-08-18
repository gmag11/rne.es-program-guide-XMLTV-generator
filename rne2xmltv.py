# coding=utf8

import requests
from bs4 import BeautifulSoup
import time
import datetime
from lxml import etree


# FUNCTION get_soup_from
#   RETURNS a html soup from an url 
#   PARAMETER url: full url pointing the html page to download
def get_soup_from (url):
  html=requests.get(url)
  soup=BeautifulSoup(html.content,'html.parser')
  return soup
  
# FUNCTION get_rne_channel_list
#   RETURNS a list of channel names and their index names
#   PARAMETER soup: html soup from RNE program schedule
def get_rne_channel_list (soup):
  channels_html=soup.find_all('ul',rel='tve')
  channels = list()
  
  for channel_soup in channels_html:
    chan=dict()
    chan['channel_display_name']=channel_soup.contents[1].text.encode('utf8')
    chan['channel_id']=channel_soup.get('class')[1].encode('utf8')
    channels.append(chan)

  print str(len(channels)) + ' channels listed'
  return channels

# FUNCTION process_program_info
#   RETURNS a program. A dictionary with keys channel_id,title,subtitle,url,podcast,start_time,stop_time,
#                                   desc,credit_director,language,video,sound
#   PARAMETER soup: html soup that contains a single program info
#   PARAMETER program: partially filled program dictionary. Only contains title and url
def process_program_info (soup,program,date):
  local_time_offset = '+0100'
  
  program_time = soup.find(class_='hour').text
  
  start_time = program_time[0:program_time.find('-')].strip().replace(':','') + '00'
  stop_time = program_time[program_time.find('-')+1:].strip().replace(':','') + '00'
  start_date = time.strftime('%Y%m%d',date.timetuple())
  stop_date = start_date
  if stop_time < start_time: # add 1 day if stop time is less than start time (finish next day)
    stop_date = time.strftime('%Y%m%d',(date + datetime.timedelta(days=1)).timetuple())
    
  program['start_time'] = start_date + start_time + ' ' + local_time_offset
  program['stop_time'] = stop_date + stop_time + ' ' + local_time_offset
  
  if soup.find('a') != None:
    podcast = soup.find('a').get('href')
    if podcast != None:
      if podcast.startswith('http://www.rtve.es'):
        program['podcast'] = podcast
      else:      
        program['podcast'] = 'http://www.rtve.es' + podcast

  if soup.find(class_='chapeaux')!=None:
    program['desc'] = soup.find(class_='chapeaux').text.strip().encode('utf8')
    
  if soup.find(class_='detalle')!=None:
    if not soup.find(class_='detalle').text.encode('ascii','ignore').startswith('Ms informacin:'):
      if (soup.find(class_='detalle').find('dt')!=None) and (soup.find(class_='detalle').find('dd')!=None):
        program['credits_director'] = soup.find(class_='detalle').find('dd').text.strip().encode('utf8')
        
  program['language']='es'
  
  return program
  
# FUNCTION get_rne_program_list
#   RETURNS a list of programs
#   PARAMETER soup: html soup from RNE program schedule
#   PARAMETER channels: list of channel names and ids
#   PARAMETER date: current schedule date
def get_rne_program_list (soup,channels,date):
  channels_html=soup.find_all('ul',rel='tve')
  chan_index = 0
  programs = list()
  for channel_html in channels_html: #process every channel information  
    programs_html = channel_html.find_all('a')
    #print str(date) +' '+ channels[chan_index].get('channel_display_name').decode('utf8')
    count = 0
    for item in programs_html: #process every program data in schedule
      program = dict()
      program['title'] = item.text.strip().encode('utf8')
      program['url'] = 'http://www.rtve.es'+item.get('href')
      program['channel_id'] = channels[chan_index].get('channel_id')
      
      single_program_soup = get_soup_from (program.get('url'))
      
      program = process_program_info (single_program_soup, program, date)
      programs.append(program)
      count = count + 1
    print str(date) +' '+ channels[chan_index].get('channel_display_name').decode('utf8') + '. ' + str(count) + ' programs found'
    chan_index = chan_index + 1  
  
  print str(len(programs)) + ' programs found'
  return programs

# FUNCTION generate_xmltv
#   RETURNS a xml string according xmltv from rne schedule
#   PARAMETER schedule: schedule containing channels and programs list
def generate_xmltv (schedule):
  print 'Building XMLTV file'
  root = etree.Element('tv')
  #print schedule.get('add_info').get('generator_info_name')
  root.set('generator-info-name',schedule.get('add_info').get('generator_info_name'))
  #print schedule.get('add_info').get('generator_info_url')
  root.set('generator-info-url',schedule.get('add_info').get('generator_info_url'))
  #print schedule.get('add_info').get('source_info_url')
  root.set('source-info-url',schedule.get('add_info').get('source_info_url'))
  #print schedule.get('add_info').get('source_info_name')
  root.set('source-info-name',schedule.get('add_info').get('source_info_name'))
  #print schedule.get('add_info').get('source_data_url')
  root.set('source-data-url',schedule.get('add_info').get('source_data_url'))
  
  for channel in schedule.get('channels'):
    xmltv_channel = etree.SubElement(root,'channel')
    xmltv_channel.set('id',channel.get('channel_id'))
    xmltv_cname = etree.SubElement(xmltv_channel,'display-name')
    print channel.get('channel_display_name').decode('utf8')
    xmltv_cname.text = channel.get('channel_display_name').decode('utf8')
    
  for program in schedule.get('programs'):
    xmltv_program = etree.SubElement(root,'programme')
    xmltv_program.set('channel',program.get('channel_id'))
    xmltv_program.set('start',program.get('start_time'))
    xmltv_program.set('stop',program.get('stop_time'))
    
    title_text = program.get('title').split('. ')
      
    title = etree.SubElement(xmltv_program,'title',lang='es')
    title.text = title_text[0].strip().decode('utf8')
    if len(title_text) > 1:
      subtitle = etree.SubElement(xmltv_program,'subtitle',lang='es')
      subtitle.text = title_text[1].strip().decode('utf8')
    
    if program.get('desc') != None:
      desc = etree.SubElement(xmltv_program,'desc',lang='es')
      desc.text = program.get('desc').decode('utf8')
      
    if program.get('credits_director') != None:
      credits = etree.SubElement(xmltv_program,'credits')
      director = etree.SubElement(credits,'director')
      director.text = program.get('credits_director').decode('utf8')
      
    if program.get('language') != None:
      lang = etree.SubElement(xmltv_program,'lang')
      lang.text=program.get('language')
    
    video = etree.SubElement (xmltv_program,'video')
    video_present = etree.SubElement(video,'present')
    video_present.text = 'no'
    
    audio = etree.SubElement (xmltv_program,'audio')
    audio_present = etree.SubElement(audio,'present')
    audio_present.text = 'yes'
    audio_mode = etree.SubElement(audio,'stereo')
    audio_mode.text='stereo'
      
  print str(len(schedule.get('programs'))) + ' programs info written to xml file'
  return etree.tostring(root,pretty_print=True,encoding='utf-8',xml_declaration=True)
      
# MAIN BRANCH

url_today='http://www.rtve.es/radio/components/parrilla/mod_parrilla_rne_hoy.inc'
url_tomorrow='http://www.rtve.es/radio/components/parrilla/mod_parrilla_rne_manana.inc'
url_past_tomorrow='http://www.rtve.es/radio/components/parrilla/mod_parrilla_rne_pasado.inc'

today_soup = get_soup_from (url_today)
print url_today + ' downloaded'
tomorrow_soup = get_soup_from (url_tomorrow)
print url_tomorrow + ' downloaded'
past_tomorrow_soup = get_soup_from (url_past_tomorrow)
print url_past_tomorrow + ' downloaded'

today_date=datetime.date.today()
tomorrow_date=(today_date + datetime.timedelta(days=1))
past_tomorrow_date=(today_date + datetime.timedelta(days=2))

channels = get_rne_channel_list(today_soup)

today_programs = get_rne_program_list (today_soup,channels,today_date)
tomorrow_programs = get_rne_program_list (tomorrow_soup,channels,tomorrow_date)
past_tomorrow_programs = get_rne_program_list (past_tomorrow_soup,channels,past_tomorrow_date)

add_info_schedule=dict()

generator_info_name=u'Python RNE XMLTV generator'
generator_info_url=u''
source_info_name=u'Radio Nacional de España. RTVE.es'
source_info_url=u'http://www.rtve.es/radio/programas/radio/'

add_info_schedule['generator_info_name']=generator_info_name
add_info_schedule['generator_info_url']=generator_info_url
add_info_schedule['source_info_name']=source_info_name
add_info_schedule['source_info_url']=source_info_url
add_info_schedule['source_data_url']=url_today

rne_schedule=dict()
rne_schedule['channels'] = channels
rne_schedule['add_info'] = add_info_schedule
rne_schedule['programs'] = today_programs + tomorrow_programs + past_tomorrow_programs

xmltv_string = generate_xmltv (rne_schedule)

xml_file_name = 'parrilla_rtve.xml'

a_prog = open(xml_file_name,'w')

a_prog.write (xmltv_string)

a_prog.close()
