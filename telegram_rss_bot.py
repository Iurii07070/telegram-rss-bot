import requests
a = requests.get('http://feeds.bbci.co.uk/news/rss.xml')
print(a.text[:1000])
