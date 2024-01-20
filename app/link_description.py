import requests
from bs4 import BeautifulSoup


def get_meta_description(url: str):
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")

    metas = soup.find_all('meta')

    print([ meta.attrs['content'] for meta in metas if 'name' in meta.attrs and meta.attrs['name'] == 'description' ])

if __name__=='__main__':
    URL = "https://docs.python.org/3/tutorial/index.html"
    meta = get_meta_description(URL)
    print(meta)