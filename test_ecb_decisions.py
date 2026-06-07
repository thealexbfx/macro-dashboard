import requests

url = "https://www.ecb.europa.eu/search/html/index.en.html?q=monetary%20policy%20decisions%202026"
html = requests.get(url, timeout=30).text

print("Length:", len(html))

for term in ["ecb.mp260430", "mp260430", "/press/pr/date/2026/html/", "30 April 2026"]:
    idx = html.find(term)
    print(term, idx)
    if idx != -1:
        print(html[idx-300:idx+500])