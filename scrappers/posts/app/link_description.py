import requests
from typing import Union

from bs4 import BeautifulSoup


def get_meta_description(url: str) -> Union[str, None]:
    try:
        breakpoint()
        page = requests.get(url)

        soup = BeautifulSoup(page.content, "html.parser")

        metas = soup.find_all('meta')

        meta = [ meta.attrs['content'] for meta in metas if 'name' in meta.attrs and meta.attrs['name'] == 'description' ]
        return meta[0] if meta else None
    except requests.exceptions.MissingSchema:
        return None
    

if __name__=='__main__':
    URL = 'https://twitter.com/iamkennethchan/status/1753536509574299863?t=rm_4LU5UuNblDCp-Me_Tug&s=19'
    meta = get_meta_description(URL)
    print(meta)