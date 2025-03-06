import requests


class Query(object):
    SRR = None
    results = None

    def __iter__(self):
        # print(self._request().json())
        if self.results is None:
            try:
                self.results = self._request().json()["organisms"]
            except:
                print(self._request().json())
        for result in self.results:
            yield result

    def filter(self, **kwargs):
        for field, value in kwargs.items():
            if field == "SRR":
                self.SRR = value
        return self

    def _request(self):
        url = f"https://files.jgi.doe.gov/search/?q=SRR:`{self.SRR}`&t=advanced"
        return requests.get(url)
