import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlencode, urljoin

from juriscraper.lib.date_utils import make_date_range_tuples
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    days_interval = 15
    first_opinion_date = datetime(1995, 6, 1).date()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.base_url = "https://www.wicourts.gov/supreme/scopin.jsp"
        self.status = "Published"
        self.set_url()
        self.cite_regex = (
            r"(?P<volume>20\d{2})\s(?P<reporter>WI)\s(?P<page>\d+)"
        )
        self.make_backscrape_iterable(kwargs)

    def set_url(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> None:
        """Sets URL with appropriate query parameters

        :param start: start date
        :param end: end date
        :return None
        """
        if not start:
            start = datetime.today() - timedelta(days=15)
            end = datetime.today()

        start = start.strftime("%m-%d-%Y")
        end = end.strftime("%m-%d-%Y")

        params = {
            "range": "None",
            "begin_date": start,
            "end_date": end,
            "sortBy": "date",
            "Submit": "Search",
        }
        self.url = f"{self.base_url}?{urlencode(params)}"

    def _process_html(self) -> None:
        """Process the HTML from wisconsin

        :return: None
        """
        for row in self.html.xpath(".//table/tbody/tr"):
            date, docket, caption, link = row.xpath("./td")
            self.cases.append(
                {
                    "date": date.text,
                    "name": caption.text,
                    "url": urljoin(
                        "https://www.wicourts.gov",
                        link.xpath("./input")[0].name,
                    ),
                    "docket": docket.text,
                }
            )

    def extract_from_text(self, scraped_text: str) -> dict:
        """Extract citation from text

        :param scraped_text: Text of scraped content
        :return: date filed
        """
        first_line = scraped_text[:100].splitlines()[0]
        match = re.search(self.cite_regex, first_line)

        if match:
            return {"Citation": {**match.groupdict(), "type": 8}}
        return {}

    def make_backscrape_iterable(self, kwargs: dict) -> None:
        """Make backscrape itearble

        Checks if backscrape start and end arguments have been passed
        by caller, and parses them accordingly

        :param kwargs: passed when initializing the scraper, may or
            may not contain backscrape controlling arguments
        :return None
        """
        start = kwargs.get("backscrape_start")
        end = kwargs.get("backscrape_end")

        if start:
            start = datetime.strptime(start, "%m/%d/%Y")
        else:
            start = self.first_opinion_date
        if end:
            end = datetime.strptime(end, "%m/%d/%Y")
        else:
            end = datetime.now()

        self.back_scrape_iterable = make_date_range_tuples(
            start, end, self.days_interval
        )

    def _download_backwards(self, dates: Tuple[date]) -> None:
        """Set date range from backscraping args and scrape

        :param dates: (start_date, end_date) tuple
        :return None
        """
        self.set_url(*dates)
        self.html = self._download()
        self._process_html()
