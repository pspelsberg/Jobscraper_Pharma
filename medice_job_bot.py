import os
import re
import sys
import smtplib
import ssl
import base64
import json
from datetime import datetime, date, timedelta
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, select_autoescape

# --- CONFIGURATION (Environment variables with safe defaults) ---
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except Exception as e:
        print(f"Info: Could not load .env file: {e}")

# Email Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USERNAME)
TO_EMAIL = os.environ.get("TO_EMAIL", "")

# Job Filter Configuration
DAYS_WINDOW = int(os.environ.get("DAYS_WINDOW", 3))
TEST_RUN = os.environ.get("TEST_RUN", "false").lower() == "true"
SEND_EMPTY_REPORTS = os.environ.get("SEND_EMPTY_REPORTS", "false").lower() == "true"

# Harmonies company color scheme for premium HTML email design
COMPANY_COLORS = {
    # Original companies
    "MEDICE": "#00828A",
    "Sanofi": "#4f46e5",
    "AstraZeneca": "#8c1d40",
    "Pfizer": "#0066cc",
    "Chiesi": "#004b87",
    "Merck": "#1f005c",
    "Kade": "#003366",
    "Teva": "#0a2240",
    "Takeda": "#d6001c",
    "Novartis": "#ec1a3b",
    "J&J": "#d50000",
    "Aenova": "#009999",
    "B. Braun": "#007a87",
    "Berlin-Chemie": "#005fa9",
    "NextPharma": "#004b49",
    "Aristo": "#00529b",
    # Target companies (MSL & Patient Advocacy Priority)
    "Roche": "#006699",
    "MSD": "#00857c",
    "BMS": "#6b2c91",
    "AbbVie": "#002f6c",
    "Bayer": "#00bcff",
    "Boehringer Ingelheim": "#002d62",
    "Eli Lilly": "#d52b1e",
    "Amgen": "#1b4f72",
    "Gilead": "#c0392b",
    "Biogen": "#ea580c",
    "GSK": "#f36633",
    "Daiichi Sankyo": "#003399",
    "Novo Nordisk": "#003865",
    "Astellas": "#b22222",
    "UCB": "#2c3e50",
    "Vertex": "#4a148c",
    "CSL Behring": "#c0392b",
    "BioNTech": "#00a499",
    "Ipsen": "#004b87",
    "Servier": "#ff7f00",
    "Eisai": "#d81e05",
    "Alnylam": "#008080",
    "Incyte": "#005a9c",
    "Grünenthal": "#007833",
    "Sobi": "#e67e22"
}

# Premium Responsive HTML Email Template (Corporate Design Layout)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karriere-Ticker: Neue Stellenangebote</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            border: 1px solid #e2e8f0;
        }
        .header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 36px 24px;
            text-align: center;
            border-bottom: 4px solid #EE9D26;
        }
        .header h1 {
            color: #ffffff;
            margin: 0;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.025em;
        }
        .header p {
            color: #94a3b8;
            margin: 8px 0 0 0;
            font-size: 15px;
        }
        .badge {
            display: inline-block;
            background-color: #EE9D26;
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 9999px;
            margin-top: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .content {
            padding: 28px 24px;
        }
        .intro {
            font-size: 16px;
            line-height: 1.6;
            color: #475569;
            margin-bottom: 24px;
        }
        .company-section {
            margin-top: 32px;
            margin-bottom: 16px;
        }
        .company-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e2e8f0;
        }
        .job-card {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 16px;
            box-sizing: border-box;
        }
        .job-title {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 10px 0;
            line-height: 1.4;
        }
        .job-meta {
            margin-bottom: 16px;
            font-size: 13px;
            line-height: 1.7;
            color: #64748b;
        }
        .meta-tag {
            display: inline-block;
            background-color: #e2e8f0;
            color: #475569;
            padding: 3px 10px;
            border-radius: 6px;
            font-weight: 500;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .meta-date {
            background-color: #fee2e2;
            color: #ef4444;
            font-weight: 600;
        }
        .btn-wrapper {
            margin-top: 14px;
        }
        .btn {
            display: inline-block;
            color: #ffffff !important;
            text-decoration: none;
            padding: 10px 22px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .footer {
            background-color: #f1f5f9;
            padding: 28px 24px;
            text-align: center;
            font-size: 13px;
            color: #64748b;
            border-top: 1px solid #e2e8f0;
        }
        .footer a {
            color: #0f172a;
            text-decoration: underline;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Karriere-Ticker 🚀</h1>
            <p>Neue passende Stellenangebote im Check</p>
            <div class="badge">{{ total_jobs }} neue Stelle(n) gefunden</div>
        </div>
        <div class="content">
            <p class="intro">Hallo,</p>
            <p class="intro">
                {% if grouped_jobs %}
                unser Job-Bot hat neue passende Stellenangebote in den letzten <strong>{{ days_window }} Tagen</strong> identifiziert:
                {% else %}
                es wurden in den letzten <strong>{{ days_window }} Tagen</strong> keine neuen Stellenangebote veröffentlicht, die deinen Kriterien entsprechen.
                {% endif %}
            </p>
            
            {% for company, jobs in grouped_jobs.items() %}
            {% if jobs %}
            <div class="company-section">
                <h2 class="company-title" style="color: {{ company_colors.get(company, '#0f172a') }}; border-bottom-color: {{ company_colors.get(company, '#0f172a') }}33;">🏢 {{ company }} ({{ jobs|length }})</h2>
                {% for job in jobs %}
                <div class="job-card" style="border-left: 4px solid {{ company_colors.get(company, '#0f172a') }};">
                    <h3 class="job-title" style="color: {{ company_colors.get(company, '#0f172a') }};">{{ job.title }}</h3>
                    <div class="job-meta">
                        <span class="meta-tag">📍 {{ job.location }}</span>
                        {% if job.level %}
                        <span class="meta-tag">💼 {{ job.level }}</span>
                        {% endif %}
                        <span class="meta-tag meta-date">📅 Veröffentlicht: {{ job.start_date }}</span>
                    </div>
                    <div class="btn-wrapper">
                        <a href="{{ job.url }}" class="btn" style="background-color: {{ company_colors.get(company, '#0f172a') }};" target="_blank">Stellenanzeige ansehen &rarr;</a>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            {% endfor %}
            
            <p class="intro" style="margin-top: 32px; margin-bottom: 0;">
                Viel Erfolg bei der Jobsuche!<br>
                <em>Dein Karriere-Job-Bot</em>
            </p>
        </div>
        <div class="footer">
            <p>Diese E-Mail wurde automatisch von deinem persönlichen Job-Bot erstellt.</p>
        </div>
    </div>
</body>
</html>
"""

# --- DATE PARSING UTILITY ---

def parse_date(date_str):
    """
    Robust date parser supporting German, English, ISO, UNIX Timestamp, and relative formats.
    Returns a date object, or None if parsing fails.
    """
    if not date_str:
        return None
    
    if isinstance(date_str, (int, float)):
        try:
            # Handle millisecond timestamps (e.g. from AstraZeneca/Eightfold)
            if date_str > 1e11:
                date_str = date_str / 1000.0
            return datetime.fromtimestamp(date_str).date()
        except Exception:
            return None

    date_str = str(date_str).strip()
    
    if date_str.isdigit():
        try:
            val = int(date_str)
            # Handle millisecond timestamps
            if val > 1e11:
                val = val / 1000.0
            return datetime.fromtimestamp(val).date()
        except Exception:
            pass

    # 1. ISO format (YYYY-MM-DD or YYYY-M-D)
    iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # 2. German format (DD.MM.YYYY or DD.MM.YY)
    de_match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b", date_str)
    if de_match:
        day, month, year = int(de_match.group(1)), int(de_match.group(2)), int(de_match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # 2b. US Slash format (M/D/YY or MM/DD/YYYY)
    slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", date_str)
    if slash_match:
        month, day, year = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # 3. German/English month names: e.g. "Mai 21, 2026" or "26. Mai 2026" or "May 21, 2026" or "Mon Sep 07 00:00:00 UTC 2026"
    months_map = {
        "jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "may": 5,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12
    }
    
    clean_text = date_str.lower()
    for word in ["gepostet am", "posted on", "veröffentlicht am", "published on", "am", "posted"]:
        clean_text = clean_text.replace(word, " ")
    clean_text = clean_text.replace(",", " ")  # Remove commas for easier word/regex boundaries
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Clean double dots e.g. "sep.. 02"
    clean_no_dots = re.sub(r"\.+", " ", clean_text)
    clean_no_dots = re.sub(r"\s+", " ", clean_no_dots).strip()
    
    m1 = re.search(r"(\d{1,2})\s+([a-zäöüß]+)\s+(\d{4})", clean_no_dots)
    if m1:
        day = int(m1.group(1))
        month_name = m1.group(2)
        year = int(m1.group(3))
        month = months_map.get(month_name) or months_map.get(month_name[:3])
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass
                
    m2 = re.search(r"([a-zäöüß]+)\s+(\d{1,2})\s+(\d{4})", clean_no_dots)
    if m2:
        month_name = m2.group(1)
        day = int(m2.group(2))
        year = int(m2.group(3))
        month = months_map.get(month_name) or months_map.get(month_name[:3])
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # Format like "Mon Sep 07 00:00:00 UTC 2026"
    m3 = re.search(r"\b([a-zäöüß]{3,4})\s+(\d{1,2})\b.*?\b(\d{4})\b", clean_no_dots)
    if m3:
        month_name = m3.group(1)
        day = int(m3.group(2))
        year = int(m3.group(3))
        month = months_map.get(month_name) or months_map.get(month_name[:3])
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # 4. Relative dates (German/English)
    if "heute" in clean_text or "today" in clean_text or "just posted" in clean_text or "gerade eben" in clean_text:
        return date.today()
    if "gestern" in clean_text or "yesterday" in clean_text:
        return date.today() - timedelta(days=1)
        
    days_match = re.search(r'(?:vor\s+)?(\d+)\+?\s*(?:tag|day)', clean_text)
    if days_match:
        days = int(days_match.group(1))
        return date.today() - timedelta(days=days)
        
    weeks_match = re.search(r'(?:vor\s+)?(\d+)\s*(?:woche|week)', clean_text)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return date.today() - timedelta(weeks=weeks)
        
    hours_match = re.search(r'(?:vor\s+)?(\d+)\s*(?:stunde|hour)', clean_text)
    if hours_match:
        return date.today()

    return None

# --- SCRAPER CLASS HIERARCHY ---

class BaseScraper:
    def __init__(self, company_name, base_url):
        self.company_name = company_name
        self.base_url = base_url
        self.max_detail_requests = 15  # Defensive design to prevent scraping infinite pages sequentially

    def fetch_jobs(self, session):
        raise NotImplementedError("Each scraper must implement fetch_jobs")

    def _fetch_page_and_match(self, session, url, regex, group_index=1, use_raw_html=False, headers=None):
        """
        Helper method to fetch a URL and match a regex on either raw HTML or soup text.
        Reduces code duplication across custom scrapers.
        """
        try:
            r = session.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                if use_raw_html:
                    match = re.search(regex, r.text)
                else:
                    soup = BeautifulSoup(r.text, "html.parser")
                    text = soup.get_text(" ", strip=True)
                    match = re.search(regex, text)
                if match:
                    return match.group(group_index)
        except Exception as e:
            print(f"  [{self.company_name}] Failed to fetch detail page or match regex for {url}: {e}")
        return None

class SuccessFactorsScraper(BaseScraper):
    def __init__(self, company_name, domain, search_path, payload_filters=None, locale=None, location=None):
        super().__init__(company_name, f"https://{domain}{search_path}")
        self.domain = domain
        self.search_path = search_path
        self.payload_filters = payload_filters or {}
        self.locale = locale
        self.location = location

    def fetch_jobs(self, session):
        search_url = self.base_url
        print(f"[{self.company_name}] Scraping SuccessFactors via {search_url}...")
        
        locale = self.locale or ("de_DE" if any(k in (self.search_path + self.domain).lower() for k in ["de", "bbraun", "medice", "nextpharma"]) else "en_US")
        
        location_val = self.location
        if not location_val and "locationsearch=" in self.search_path:
            m_loc = re.search(r"locationsearch=([^&]+)", self.search_path)
            if m_loc:
                location_val = m_loc.group(1)
        location_val = location_val or ""

        # Try API first
        try:
            r = session.get(search_url, timeout=15)
            r.raise_for_status()
            
            csrf_match = re.search(r'var CSRFToken\s*=\s*"([^"]+)";', r.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                api_url = f"https://{self.domain}/services/recruiting/v1/jobs"
                api_headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrf_token,
                    "Referer": search_url,
                    "Origin": f"https://{self.domain}"
                }
                
                payload = {
                    "locale": locale,
                    "pageNumber": 0,
                    "sortBy": "",
                    "keywords": "",
                    "location": location_val,
                    "facetFilters": self.payload_filters,
                    "brand": "",
                    "skills": [],
                    "categoryId": 0
                }
                resp = session.post(api_url, headers=api_headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("jobSearchResult", [])
                    jobs = []
                    for item in raw_results:
                        res = item.get("response", {})
                        title = res.get("unifiedStandardTitle") or res.get("title")
                        url_title = res.get("urlTitle") or "job"
                        job_id = res.get("id")
                        if title and job_id:
                            location = res.get("jobLocationShort")
                            if isinstance(location, list):
                                location = ", ".join(location)
                            location = location or "Deutschland"
                            start_date = res.get("unifiedStandardStart")
                            job_url = f"https://{self.domain}/job/{url_title}/{job_id}-{locale}"
                            
                            level_info = None
                            if "jobLevel" in res:
                                levels = res["jobLevel"]
                                level_info = ", ".join(levels) if isinstance(levels, list) else str(levels)
                                
                            jobs.append({
                                "title": title,
                                "url": job_url,
                                "location": location,
                                "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                                "level": level_info
                            })
                    if jobs:
                        print(f"  [API] Found {len(jobs)} jobs")
                        return jobs
        except Exception as e:
            print(f"  API failed: {e}. Trying HTML fallback...")

        # HTML Fallback
        try:
            r = session.get(search_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Check for standard SuccessFactors data table (tr.data-row)
            rows = soup.find_all("tr", class_="data-row")
            if rows:
                jobs = []
                for row in rows:
                    a = row.find("a", class_="jobTitle-link") or row.find("a")
                    if not a:
                        continue
                    href = a.get("href")
                    url = f"https://{self.domain}{href}" if href.startswith("/") else href
                    title = a.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    date_span = row.find(class_="jobDate") or row.find("td", class_="colDate")
                    start_date = date_span.get_text(strip=True) if date_span else None
                    loc_span = row.find(class_="jobLocation") or row.find("td", class_="colLocation")
                    loc = loc_span.get_text(strip=True) if loc_span else "Deutschland"
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": loc,
                        "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                        "level": self.company_name
                    })
                if jobs:
                    print(f"  [HTML Table] Found {len(jobs)} jobs")
                    return jobs

            # Fallback to /job/ links and cards/tiles
            job_links = soup.find_all("a", href=re.compile(r"/job/"))
            jobs = []
            seen = set()
            for link in job_links:
                href = link.get("href")
                url = f"https://{self.domain}{href}" if href.startswith("/") else href
                if url in seen:
                    continue
                title = link.get_text(strip=True)
                if not title:
                    title = link.parent.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                seen.add(url)
                
                parent_card = link.find_parent(class_=re.compile(r"jobCard|card|row|item|tile|sub-section", re.I)) or link.parent.parent
                card_text = parent_card.get_text(" ", strip=True) if parent_card else ""
                date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{2,4})\b", card_text)
                
                start_date = None
                if date_match:
                    start_date = date_match.group(1)
                elif len(jobs) < self.max_detail_requests:
                    start_date = self._fetch_page_and_match(
                        session, url, r'(?:"datePosted"\s*:\s*"|<meta[^>]+itemprop=[\'"]datePosted[\'"][^>]+content=[\'"])([^\'">]+)', group_index=1, use_raw_html=True
                    )
                
                loc = "Deutschland"
                if "Location" in card_text:
                    m_loc = re.search(r'Location\s*([^,\n\r]+(?:,\s*[^,\n\r]+)?)', card_text)
                    if m_loc:
                        loc = m_loc.group(1).strip()

                jobs.append({
                    "title": title,
                    "url": url,
                    "location": loc,
                    "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                    "level": self.company_name
                })
            print(f"  [HTML Fallback] Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  HTML fallback failed: {e}")
            return []

class TalentBrewScraper(BaseScraper):
    def __init__(self, company_name, domain, search_path, active_facet_id, facet_type, facet_count, display):
        super().__init__(company_name, f"https://{domain}{search_path}")
        self.domain = domain
        self.search_path = search_path
        self.active_facet_id = active_facet_id
        self.facet_type = facet_type
        self.facet_count = facet_count
        self.display = display

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping TalentBrew via {self.base_url}...")
        
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error fetching landing page: {e}")
            return []
            
        soup = BeautifulSoup(r.text, "html.parser")
        results_elem = soup.find(id="search-results")
        results_data = results_elem.attrs if results_elem else {}
        
        filter_elem = soup.find(id="search-filters")
        filter_data = filter_elem.attrs if filter_elem else {}
        
        de_checkbox = soup.find("input", class_="filter-checkbox", attrs={"data-display": self.display})
        active_facet_id = self.active_facet_id
        facet_type = self.facet_type
        facet_count = self.facet_count
        if de_checkbox:
            active_facet_id = de_checkbox.get("data-id", self.active_facet_id)
            facet_type = de_checkbox.get("data-facet-type", self.facet_type)
            facet_count = de_checkbox.get("data-count", self.facet_count)

        ajax_url = f"https://{self.domain}/search-jobs/results"
        
        page = 1
        jobs = []
        seen_urls = set()
        
        while page <= 5:
            params = {
                "ActiveFacetID": active_facet_id,
                "CurrentPage": str(page),
                "RecordsPerPage": results_data.get("data-records-per-page", "15"),
                "TotalPages": results_data.get("data-total-pages", "0"),
                "TotalResults": results_data.get("data-total-results", "0"),
                "Distance": results_data.get("data-distance", "50"),
                "Keywords": results_data.get("data-keywords", ""),
                "Location": results_data.get("data-location", ""),
                "Latitude": results_data.get("data-latitude", ""),
                "Longitude": results_data.get("data-longitude", ""),
                "ShowRadius": results_data.get("data-show-radius", "False"),
                "IsPagination": "True" if page > 1 else "False",
                "CustomFacetName": results_data.get("data-custom-facet-name", ""),
                "FacetTerm": results_data.get("data-facet-term", ""),
                "FacetType": results_data.get("data-facet-type", "0"),
                "SearchResultsModuleName": results_data.get("data-search-results-module-name", "Search Results"),
                "SearchFiltersModuleName": filter_data.get("data-search-filters-module-name", "Search Filters"),
                "SortCriteria": "1",
                "SortDirection": "0",
                "SearchType": results_data.get("data-search-type", "5"),
                "ResultsType": results_data.get("data-results-type", "0"),
                "OrganizationIds": results_data.get("data-organization-ids", ""),
                
                "FacetFilters[0].ID": active_facet_id,
                "FacetFilters[0].FacetType": facet_type,
                "FacetFilters[0].Count": facet_count,
                "FacetFilters[0].Display": self.display,
                "FacetFilters[0].IsApplied": "true",
                "FacetFilters[0].FieldName": ""
            }
            
            try:
                r2 = session.get(ajax_url, params=params, headers={"Referer": self.base_url, "X-Requested-With": "XMLHttpRequest"}, timeout=15)
                r2.raise_for_status()
                data = r2.json()
            except Exception as e:
                print(f"  Error fetching page {page} results: {e}")
                break
                
            if not data.get("hasJobs", False):
                break
                
            soup2 = BeautifulSoup(data.get("results", ""), "html.parser")
            job_links = soup2.find_all("a", href=re.compile(r"/stellenbeschreibung/|/job-details/|/job/"))
            if not job_links:
                break
                
            page_jobs_processed = 0
            for a in job_links:
                href = a["href"]
                url = f"https://{self.domain}{href}" if href.startswith("/") else href
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                page_jobs_processed += 1
                
                title_tag = a.find(["h2", "h3"]) or a
                title = title_tag.get_text(strip=True)
                
                location = self.display
                loc_tag = a.find(class_=re.compile("job-location|location", re.I))
                if loc_tag:
                    location = loc_tag.get_text(strip=True).replace("Standort:", "").strip()
                    
                category = self.company_name
                cat_tag = a.find(class_=re.compile("job-category|category", re.I))
                if cat_tag:
                    category = cat_tag.get_text(strip=True).replace("Kategorie:", "").strip()
                    
                date_text = None
                try:
                    rj = session.get(url, timeout=10)
                    if rj.status_code == 200:
                        soup_j = BeautifulSoup(rj.text, "html.parser")
                        date_tag = soup_j.find(class_=re.compile("job-date|date-posted|posted-date", re.I))
                        if date_tag:
                            date_text = date_tag.get_text(strip=True)
                        else:
                            m_date = re.search(r'"datePosted"\s*:\s*"([^"]+)"', rj.text)
                            if m_date:
                                date_text = m_date.group(1)
                except Exception:
                    pass
                    
                jobs.append({
                    "title": title,
                    "url": url,
                    "location": location,
                    "start_date": date_text or datetime.now().strftime("%d.%m.%y"),
                    "level": category
                })
                
            if page_jobs_processed == 0:
                break
            page += 1
            
        print(f"  Found {len(jobs)} jobs")
        return jobs

class AstraZenecaScraper(BaseScraper):
    def __init__(self):
        super().__init__("AstraZeneca", "https://astrazeneca.eightfold.ai/api/pcsx/search?domain=astrazeneca.com&location=Germany")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping AstraZeneca Eightfold PCSX API...")
        jobs = []
        start = 0
        try:
            while len(jobs) < 50:
                api_url = f"{self.base_url}&start={start}"
                r = session.get(api_url, timeout=15)
                r.raise_for_status()
                data = r.json()
                positions = data.get("data", {}).get("positions", [])
                if not positions:
                    break
                for item in positions:
                    title = item.get("name")
                    job_id = item.get("id")
                    pos_url = item.get("positionUrl")
                    url = f"https://astrazeneca.eightfold.ai{pos_url}" if pos_url else f"https://astrazeneca.eightfold.ai/careers/job/{job_id}"
                    locations = item.get("locations", [])
                    location = ", ".join(locations) if locations else "Deutschland"
                    pub_timestamp = item.get("postedTs") or item.get("creationTs")
                    if title and job_id:
                        jobs.append({
                            "title": title,
                            "url": url,
                            "location": location,
                            "start_date": pub_timestamp or datetime.now().strftime("%d.%m.%y"),
                            "level": item.get("department")
                        })
                count = data.get("data", {}).get("count", 0)
                start += len(positions)
                if start >= count:
                    break
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  AstraZeneca scraping failed: {e}")
            return []

class WorkdayScraper(BaseScraper):
    def __init__(self, company_name, host, tenant, site, search_text="Germany", applied_facets=None, limit=20, url_prefix=None):
        self.host = host
        self.tenant = tenant
        self.site = site
        self.search_text = search_text
        self.applied_facets = applied_facets or {}
        self.limit = limit
        self.url_prefix = url_prefix or f"https://{host}/{site}"
        super().__init__(company_name, f"https://{host}/wday/cxs/{tenant}/{site}/jobs")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Workday CXS API...")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "limit": self.limit,
            "offset": 0,
            "searchText": self.search_text,
            "appliedFacets": self.applied_facets
        }
        try:
            r = session.post(self.base_url, json=payload, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            raw_postings = data.get("jobPostings", [])
            jobs = []
            for posting in raw_postings:
                title = posting.get("title")
                path = posting.get("externalPath")
                posted_date = posting.get("postedOn")
                location = posting.get("locationsText", "Deutschland")
                if title and path:
                    if not posted_date and len(jobs) < self.max_detail_requests:
                        try:
                            det_url = f"https://{self.host}/wday/cxs/{self.tenant}/{self.site}{path}"
                            r_det = session.get(det_url, headers={"Accept": "application/json"}, timeout=10)
                            if r_det.status_code == 200:
                                d_info = r_det.json().get("jobPostingInfo", {})
                                posted_date = d_info.get("postedOn") or d_info.get("startDate")
                        except Exception:
                            pass
                    job_url = f"{self.url_prefix}{path}"
                    jobs.append({
                        "title": title,
                        "url": job_url,
                        "location": location,
                        "start_date": posted_date or datetime.now().strftime("%d.%m.%y"),
                        "level": self.company_name
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  {self.company_name} Workday API failed: {e}")
            return []

class PfizerScraper(WorkdayScraper):
    def __init__(self):
        super().__init__(
            "Pfizer", 
            "pfizer.wd1.myworkdayjobs.com", 
            "pfizer", 
            "PfizerCareers", 
            search_text="", 
            applied_facets={"Location_Country": ["dcc5b7608d8644b3a93716604e78e995"]},
            url_prefix="https://pfizer.wd1.myworkdayjobs.com/pfizer/PfizerCareers"
        )

class PhenomScraper(BaseScraper):
    def __init__(self, company_name, search_url, job_base_url, max_offsets=(0, 10, 20)):
        super().__init__(company_name, search_url)
        self.job_base_url = job_base_url.rstrip("/")
        self.max_offsets = max_offsets

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Phenom DDO state...")
        jobs = []
        seen = set()
        for offset in self.max_offsets:
            sep = "&" if "?" in self.base_url else "?"
            url = f"{self.base_url}{sep}from={offset}"
            try:
                r = session.get(url, timeout=15)
                r.raise_for_status()
                m = re.search(r'phApp\.ddo\s*=\s*(\{.*?\});', r.text)
                if m:
                    ddo = json.loads(m.group(1))
                    raw_jobs = ddo.get('eagerLoadRefineSearch', {}).get('data', {}).get('jobs', [])
                    for j in raw_jobs:
                        title = j.get("title")
                        job_seq = j.get("jobSeqNo")
                        country = j.get("country")
                        location = j.get("location") or j.get("city") or "Deutschland"
                        posted_date = j.get("postedDate")
                        
                        is_germany = False
                        if country and country.lower() in ["germany", "deutschland", "de"]:
                            is_germany = True
                        elif location and any(k in location.lower() for k in ["germany", "deutschland", "de"]):
                            is_germany = True
                            
                        if is_germany and title and job_seq:
                            if job_seq in seen:
                                continue
                            seen.add(job_seq)
                            url_title = re.sub(r'[^a-zA-Z0-9-]', '-', title.lower())
                            url_title = re.sub(r'-+', '-', url_title).strip('-')
                            job_url = f"{self.job_base_url}/{job_seq}/{url_title}"
                            jobs.append({
                                "title": title,
                                "url": job_url,
                                "location": location,
                                "start_date": posted_date or datetime.now().strftime("%d.%m.%y"),
                                "level": j.get("category") or self.company_name
                            })
            except Exception as e:
                print(f"  [{self.company_name}] Phenom offset {offset} failed: {e}")
                break
        print(f"  Found {len(jobs)} jobs")
        return jobs

class MerckScraper(PhenomScraper):
    def __init__(self):
        super().__init__(
            "Merck", 
            "https://careers.merckgroup.com/de/de/search-results?s=1", 
            "https://careers.merckgroup.com/de/de/job",
            max_offsets=(0, 10, 20, 30, 40)
        )

class KadeScraper(BaseScraper):
    def __init__(self):
        super().__init__("Kade", "https://www.kade.de/karriere/stellenangebote/")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Kade...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            jobs = []
            seen = set()
            processed_count = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/karriere/stellenangebote/job/" in href:
                    url = f"https://www.kade.de{href}" if href.startswith("/") else href
                    if url in seen:
                        continue
                    seen.add(url)
                    
                    title = a.get_text(strip=True)
                    if not title:
                        title = a.parent.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    if processed_count >= self.max_detail_requests:
                        print(f"  [{self.company_name}] Reached max detail requests limit ({self.max_detail_requests}). Stopping.")
                        break
                        
                    start_date = self._fetch_page_and_match(
                        session, url, r"\b\d{2}\.\d{2}\.\d{4}\b", group_index=0, use_raw_html=False
                    )
                    processed_count += 1
                        
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": "Deutschland",
                        "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                        "level": "DR. KADE"
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Kade scraping failed: {e}")
            return []

class TevaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Teva", "https://www.careers.teva/careers?location=Germany")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Teva Eightfold HTML...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            script_tag = soup.find("code", id="smartApplyData")
            if not script_tag:
                print("  Error: code#smartApplyData tag not found in Teva HTML.")
                return []
            import html
            unescaped_json = html.unescape(script_tag.get_text(strip=True))
            data = json.loads(unescaped_json)
            raw_jobs = data.get("positions", [])
            jobs = []
            for item in raw_jobs:
                title = item.get("name")
                job_id = item.get("id")
                url = item.get("canonicalPositionUrl") or f"https://www.careers.teva/careers/job/{job_id}"
                locations = item.get("locations", [])
                location = ", ".join(locations) if locations else "Deutschland"
                pub_timestamp = item.get("t_create") or item.get("t_update")
                if title and job_id:
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": location,
                        "start_date": pub_timestamp or datetime.now().strftime("%d.%m.%y"),
                        "level": item.get("department", "Teva / ratiopharm")
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Teva scraping failed: {e}")
            return []

class NovartisScraper(BaseScraper):
    def __init__(self):
        super().__init__("Novartis", "https://www.novartis.com/de-de/careers/career-search?country%5B0%5D=LOC_DE&field_alternative_country%5B0%5D=LOC_DE")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Novartis HTML Table...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            jobs = []
            if table:
                rows = table.find_all("tr")[1:]
                for tr in rows:
                    cols = tr.find_all("td")
                    if len(cols) >= 5:
                        title_cell = cols[0]
                        business = cols[1].get_text(strip=True)
                        location = cols[3].get_text(strip=True)
                        date_text = cols[4].get_text(strip=True)
                        
                        a = title_cell.find("a", href=True)
                        if a:
                            title = a.get_text(strip=True)
                            title = re.sub(r'Regulär.*|Regular.*|Befristet.*|Temporary.*', '', title).strip()
                            href = a["href"]
                            url = f"https://www.novartis.com{href}" if href.startswith("/") else href
                            
                            jobs.append({
                                "title": title,
                                "url": url,
                                "location": f"{location}, Deutschland",
                                "start_date": date_text,
                                "level": business
                            })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Novartis scraping failed: {e}")
            return []

class JNJScraper(BaseScraper):
    def __init__(self):
        super().__init__("J&J", "https://www.careers.jnj.com/en/jobs/?search=&country=Germany&pagesize=20#results")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping J&J Career List...")
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        try:
            r = session.get(self.base_url, headers=headers, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            jobs = []
            seen = set()
            processed_count = 0
            job_links = soup.find_all('a', href=re.compile(r'/jobs/r-'))
            for link in job_links:
                href = link['href']
                url = f"https://www.careers.jnj.com{href}" if href.startswith("/") else href
                if url in seen:
                    continue
                seen.add(url)
                
                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                
                if processed_count >= self.max_detail_requests:
                    print(f"  [{self.company_name}] Reached max detail requests limit ({self.max_detail_requests}). Stopping.")
                    break
                
                start_date = self._fetch_page_and_match(
                    session, url, r'"datePosted"\s*:\s*"([^"]+)"', group_index=1, use_raw_html=True, headers=headers
                )
                processed_count += 1
                    
                jobs.append({
                    "title": title,
                    "url": url,
                    "location": "Deutschland",
                    "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                    "level": "J&J"
                })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  J&J scraping failed: {e}")
            return []

class AenovaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Aenova", "https://aenova-group.onlyfy.jobs/candidate/job/ajax_list?display_length=100&page=1&sort=date&sort_dir=DESC")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Aenova onlyfy AJAX...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            jobs = []
            for row in soup.find_all(class_=re.compile("row-table")):
                title_a = row.find("strong", class_="job-title").find("a") if row.find("strong", class_="job-title") else None
                if not title_a:
                    continue
                title = title_a.get_text(strip=True)
                href = title_a.get("href")
                url = f"https://aenova-group.onlyfy.jobs{href}" if href.startswith("/") else href
                
                loc_div = row.find(class_=re.compile("icon-map-marker"))
                location = loc_div.parent.get_text(strip=True) if loc_div else "Deutschland"
                
                date_str = None
                for cell in row.find_all(class_=re.compile("cell-table")):
                    text = cell.get_text(strip=True)
                    if re.match(r"^\d{2}\.\d{2}\.\d{2,4}$", text):
                        date_str = text
                        break
                        
                jobs.append({
                    "title": title,
                    "url": url,
                    "location": location,
                    "start_date": date_str or datetime.now().strftime("%d.%m.%y"),
                    "level": "Aenova"
                })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Aenova scraping failed: {e}")
            return []

class BerlinChemieScraper(BaseScraper):
    def __init__(self):
        super().__init__("Berlin-Chemie", "https://karriere.berlin-chemie.de/search")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Berlin-Chemie...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            
            # Try Typesense with specific key first
            candidates = re.findall(r'[A-Za-z0-9+/]{40,320}={0,2}', r.text)
            found_key = None
            filter_by_policy = None
            
            for c in candidates:
                if len(c) > 60:
                    try:
                        decoded = base64.b64decode(c).decode('utf-8', errors='ignore')
                        if 'berlin-chemie' in decoded:
                            m_policy = re.search(r'"filter_by"\s*:\s*"([^"]+)"', decoded)
                            if m_policy:
                                policy = m_policy.group(1)
                                if 'aussendienst' in policy or 'professionals' in policy:
                                    found_key = c
                                    filter_by_policy = policy
                                    break
                                elif not found_key:
                                    found_key = c
                                    filter_by_policy = policy
                    except Exception:
                        pass
                        
            if found_key and filter_by_policy:
                api_url = "https://api.my-job-shop.com/api/typesense/multi_search"
                headers = {
                    "Content-Type": "application/json",
                    "X-Typesense-API-Key": found_key,
                    "Origin": "https://karriere.berlin-chemie.de",
                    "Referer": "https://karriere.berlin-chemie.de/"
                }
                payload = {
                    "searches": [
                        {
                            "collection": "offers",
                            "q": "*",
                            "query_by": "title",
                            "filter_by": filter_by_policy,
                            "page": 1,
                            "per_page": 50,
                            "sort_by": "create_date_timestamp:desc"
                        }
                    ]
                }
                resp = session.post(f"{api_url}?x-typesense-api-key={found_key}", json=payload, headers=headers, timeout=15)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        hits = results[0].get("hits", [])
                        jobs = []
                        for hit in hits:
                            doc = hit.get("document", {})
                            title = doc.get("title")
                            url = doc.get("url")
                            location = doc.get("location", "Deutschland")
                            pub_timestamp = doc.get("create_date_timestamp")
                            start_date = None
                            if pub_timestamp:
                                try:
                                    start_date = datetime.fromtimestamp(pub_timestamp).strftime("%d.%m.%y")
                                except Exception:
                                    pass
                            if title and url:
                                jobs.append({
                                    "title": title,
                                    "url": url,
                                    "location": location,
                                    "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                                    "level": doc.get("department", "Berlin-Chemie")
                                })
                        if jobs:
                            print(f"  [Typesense] Found {len(jobs)} jobs")
                            return jobs
            
            # HTML Fallback from search page
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/jobs/" in href and href not in seen:
                    seen.add(href)
                    title = a.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    url = href if href.startswith("http") else f"https://karriere.berlin-chemie.de{href}"
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": "Deutschland",
                        "start_date": datetime.now().strftime("%d.%m.%y"),
                        "level": "Berlin-Chemie"
                    })
            print(f"  [HTML Fallback] Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Berlin-Chemie scraping failed: {e}")
            return []

class AristoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Aristo", "https://www.aristo-pharma.de/de/karriere")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Aristo...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            jobs = []
            seen = set()
            processed_count = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/de/karriere/") and href != "/de/karriere/":
                    url = f"https://www.aristo-pharma.de{href}"
                    if url in seen:
                        continue
                    seen.add(url)
                    
                    title = a.get_text(strip=True)
                    if not title:
                        title = a.parent.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    if processed_count >= self.max_detail_requests:
                        print(f"  [{self.company_name}] Reached max detail requests limit ({self.max_detail_requests}). Stopping.")
                        break
                        
                    start_date = self._fetch_page_and_match(
                        session, url, r"\b\d{1,2}\.\s+[a-zA-Zäöüß]+\s+\d{4}\b", group_index=0, use_raw_html=False
                    )
                    processed_count += 1
                        
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": "Deutschland",
                        "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                        "level": "Aristo Pharma"
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Aristo scraping failed: {e}")
            return []

class GreenhouseScraper(BaseScraper):
    def __init__(self, company_name, board_token, location_filter="germany"):
        super().__init__(company_name, f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs")
        self.location_filter = location_filter.lower()

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Greenhouse API...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            data = r.json()
            jobs = []
            for j in data.get("jobs", []):
                loc_name = (j.get("location", {}).get("name") or "").lower()
                if self.location_filter in loc_name or "deutschland" in loc_name:
                    jobs.append({
                        "title": j.get("title"),
                        "url": j.get("absolute_url"),
                        "location": j.get("location", {}).get("name", "Deutschland"),
                        "start_date": j.get("updated_at"),
                        "level": self.company_name
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  {self.company_name} Greenhouse scraping failed: {e}")
            return []

class SmartRecruitersScraper(BaseScraper):
    def __init__(self, company_name, company_identifier, country_filter="de"):
        super().__init__(company_name, f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings")
        self.company_identifier = company_identifier
        self.country_filter = country_filter.lower()

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping SmartRecruiters API...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            data = r.json()
            jobs = []
            for j in data.get("content", []):
                country = (j.get("location", {}).get("country") or "").lower()
                if country == self.country_filter or "germany" in country or "deutschland" in country:
                    job_id = j.get("id")
                    loc = j.get("location", {}).get("fullLocation") or j.get("location", {}).get("city") or "Deutschland"
                    job_url = f"https://jobs.smartrecruiters.com/{self.company_identifier}/{job_id}"
                    jobs.append({
                        "title": j.get("name"),
                        "url": job_url,
                        "location": loc,
                        "start_date": j.get("releasedDate"),
                        "level": j.get("department") or self.company_name
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  {self.company_name} SmartRecruiters scraping failed: {e}")
            return []

class JibeScraper(BaseScraper):
    def __init__(self, company_name, domain, location="Germany"):
        super().__init__(company_name, f"https://{domain}/api/jobs?location={location}")
        self.domain = domain

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Jibe API...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            data = r.json()
            jobs = []
            for item in data.get("jobs", []):
                doc = item.get("data", {})
                title = doc.get("title")
                slug = doc.get("slug")
                if title and slug:
                    url = f"https://{self.domain}/jobs/{slug}"
                    loc = doc.get("full_location") or doc.get("city") or "Deutschland"
                    posted = doc.get("create_date") or doc.get("posted_date")
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": loc,
                        "start_date": posted,
                        "level": self.company_name
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  {self.company_name} Jibe scraping failed: {e}")
            return []

class AbbVieScraper(BaseScraper):
    def __init__(self):
        super().__init__("AbbVie", "https://careers.abbvie.com/en/jobs?q=Germany")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping AbbVie careers...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            job_links = soup.find_all("a", href=re.compile(r"/en/job/"))
            jobs = []
            seen = set()
            processed_count = 0
            for link in job_links:
                href = link.get("href")
                url = f"https://careers.abbvie.com{href}" if href.startswith("/") else href
                if url in seen:
                    continue
                seen.add(url)
                title = link.get_text(strip=True)
                if not title or title.lower() in ["learn more", "apply"]:
                    continue
                if len(title) < 5:
                    continue
                
                card = link.find_parent(class_=re.compile(r"card|job", re.I)) or link.parent.parent
                location = "Deutschland"
                if card:
                    card_text = card.get_text(" | ", strip=True)
                    m_loc = re.search(r'Location\s*\|\s*([^|]+)', card_text)
                    if m_loc:
                        location = m_loc.group(1).strip()

                start_date = None
                if processed_count < self.max_detail_requests:
                    start_date = self._fetch_page_and_match(
                        session, url, r'"datePosted"\s*:\s*"([^"]+)"', group_index=1, use_raw_html=True
                    )
                    processed_count += 1

                jobs.append({
                    "title": title,
                    "url": url,
                    "location": location,
                    "start_date": start_date or datetime.now().strftime("%d.%m.%y"),
                    "level": "AbbVie"
                })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  AbbVie scraping failed: {e}")
            return []

class EisaiScraper(BaseScraper):
    def __init__(self):
        super().__init__("Eisai", "https://www.eisai.de/karriere/stellenangebote/stellenanzeigen-deutschland/")

    def fetch_jobs(self, session):
        print(f"[{self.company_name}] Scraping Eisai Deutschland...")
        try:
            r = session.get(self.base_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            prefix = "/karriere/stellenangebote/stellenanzeigen-deutschland/"
            jobs = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith(prefix) and href != prefix:
                    url = f"https://www.eisai.de{href}" if href.startswith("/") else href
                    if url in seen:
                        continue
                    seen.add(url)
                    title = a.get_text(strip=True)
                    if not title or len(title) < 5 or "stellenanzeigen" in title.lower():
                        continue
                    jobs.append({
                        "title": title,
                        "url": url,
                        "location": "Frankfurt am Main, Deutschland",
                        "start_date": datetime.now().strftime("%d.%m.%y"),
                        "level": "Eisai Deutschland"
                    })
            print(f"  Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"  Eisai scraping failed: {e}")
            return []

# --- SCRAPER REGISTRY ---

SCRAPERS = [
    # --- Top Pharma Prioritätsliste (MSL, Medical Affairs & Patient Advocacy) ---
    WorkdayScraper(
        "Roche", 
        "roche.wd3.myworkdayjobs.com", 
        "roche", 
        "roche-ext", 
        search_text="Germany"
    ),
    NovartisScraper(),
    AstraZenecaScraper(),
    PhenomScraper(
        "MSD", 
        "https://jobs.msd.com/gb/en/search-results?keywords=Germany", 
        "https://jobs.msd.com/gb/en/job"
    ),
    WorkdayScraper(
        "BMS", 
        "bristolmyerssquibb.wd5.myworkdayjobs.com", 
        "bristolmyerssquibb", 
        "BMS", 
        search_text="Germany"
    ),
    AbbVieScraper(),
    JNJScraper(),
    TalentBrewScraper(
        "Sanofi",
        "jobs.sanofi.com",
        "/de/jobsuche",
        "2921044", "2", "50", "Deutschland"
    ),
    PfizerScraper(),
    SuccessFactorsScraper(
        "Bayer",
        "jobs.bayer.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    SuccessFactorsScraper(
        "Boehringer Ingelheim",
        "jobs.boehringer-ingelheim.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    WorkdayScraper(
        "Eli Lilly", 
        "lilly.wd115.myworkdayjobs.com", 
        "lilly", 
        "LLY", 
        search_text="Germany"
    ),
    TalentBrewScraper(
        "Takeda",
        "jobs.takeda.com",
        "/search-jobs/Germany/1113/2/2921044/51x5/10x5/50/2",
        "2921044", "2", "50", "Germany"
    ),
    WorkdayScraper(
        "Amgen", 
        "amgen.wd1.myworkdayjobs.com", 
        "amgen", 
        "Careers", 
        search_text="Germany",
        applied_facets={"LocationCountry": ["dcc5b7608d8644b3a93716604e78e995"]}
    ),
    WorkdayScraper(
        "Gilead", 
        "gilead.wd1.myworkdayjobs.com", 
        "gilead", 
        "gileadcareers", 
        search_text="Germany"
    ),
    MerckScraper(),
    WorkdayScraper(
        "Biogen", 
        "biibhr.wd3.myworkdayjobs.com", 
        "biibhr", 
        "external", 
        search_text="Germany"
    ),
    PhenomScraper(
        "GSK", 
        "https://jobs.gsk.com/gb/en/search-results?keywords=Germany", 
        "https://jobs.gsk.com/gb/en/job"
    ),
    SuccessFactorsScraper(
        "Daiichi Sankyo",
        "careers.daiichisankyo.com",
        "/search/?q=&locationsearch=Germany",
        location="Germany",
        locale="en_US"
    ),
    SuccessFactorsScraper(
        "Novo Nordisk",
        "careers.novonordisk.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    SuccessFactorsScraper(
        "Astellas",
        "careers.astellas.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="en_US"
    ),
    PhenomScraper(
        "UCB", 
        "https://careers.ucb.com/global/en/search-results?keywords=Germany", 
        "https://careers.ucb.com/global/en/job"
    ),
    WorkdayScraper(
        "Vertex", 
        "vrtx.wd501.myworkdayjobs.com", 
        "vrtx", 
        "Vertex_Careers", 
        search_text="Germany"
    ),
    WorkdayScraper(
        "CSL Behring", 
        "csl.wd1.myworkdayjobs.com", 
        "csl", 
        "CSL_External", 
        search_text="Germany"
    ),
    SuccessFactorsScraper(
        "BioNTech",
        "jobs.biontech.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    WorkdayScraper(
        "Ipsen", 
        "ipsen.wd103.myworkdayjobs.com", 
        "ipsen", 
        "Ipsen_Careers", 
        search_text="Germany"
    ),
    SuccessFactorsScraper(
        "Servier",
        "jobs.servier.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    EisaiScraper(),
    GreenhouseScraper("Alnylam", "alnylampharmaceuticals"),
    JibeScraper("Incyte", "careers.incyte.com", location="Germany"),
    SuccessFactorsScraper(
        "Grünenthal",
        "careers.grunenthal.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    SmartRecruitersScraper("Sobi", "sobi"),

    # --- Weitere etablierte Pharmaunternehmen (Bestehende Scraper) ---
    SuccessFactorsScraper(
        "MEDICE", 
        "career.medice-health-family.com", 
        "/search/?q=&locationsearch=iserlohn&searchResultView=LIST&pageNumber=0&facetFilters=%7B%22sfstd_jobLocation_obj%22%3A%5B%22Iserlohn%22%5D%2C%22cust_businessArea%22%3A%5B%22MEDICE%22%5D%2C%22jobLevel%22%3A%5B%22Berufserfahrene%22%2C%22Team-Leitung%22%5D%7D",
        {"sfstd_jobLocation_obj": ["Iserlohn"], "cust_businessArea": ["MEDICE"], "jobLevel": ["Berufserfahrene", "Team-Leitung"]},
        locale="de_DE"
    ),
    SuccessFactorsScraper(
        "Chiesi",
        "careers.chiesi.com",
        "/search/?createNewAlert=false&q=&optionsFacetsDD_country=DE",
        {"optionsFacetsDD_country": ["DE"]}
    ),
    KadeScraper(),
    TevaScraper(),
    AenovaScraper(),
    SuccessFactorsScraper(
        "B. Braun",
        "jobs.bbraun.com",
        "/search/?q=&facetFilters=%7B%22cust_country%22%3A%5B%22Deutschland%22%5D%7D",
        {"cust_country": ["Deutschland"]},
        locale="de_DE"
    ),
    BerlinChemieScraper(),
    SuccessFactorsScraper(
        "NextPharma",
        "careers.nextpharma.com",
        "/search/?q=&locationsearch=Germany",
        {"locationsearch": "Germany"},
        locale="de_DE"
    ),
    AristoScraper()
]
def send_combined_email_alert(grouped_jobs):
    """
    Renders the premium HTML template and sends the alert email.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, TO_EMAIL]):
        print("Error: SMTP configuration is incomplete. Check environment variables!")
        sys.exit(1)
        
    total_jobs = sum(len(jobs) for jobs in grouped_jobs.values())
        
    env = Environment(autoescape=select_autoescape(["html", "xml"]))
    template = env.from_string(HTML_TEMPLATE)
    
    html_content = template.render(
        grouped_jobs=grouped_jobs,
        total_jobs=total_jobs,
        days_window=DAYS_WINDOW,
        company_colors=COMPANY_COLORS
    )
    
    # Text fallback compilation
    text_content = f"Karriere-Ticker 🚀\n\nHallo,\n\nes wurden {total_jobs} neue Stellenangebote in den letzten {DAYS_WINDOW} Tagen gefunden:\n\n"
    
    for company, jobs in grouped_jobs.items():
        if jobs:
            text_content += f"--- {company} ({len(jobs)} neue Stelle/n) ---\n"
            for idx, job in enumerate(jobs, 1):
                text_content += f"{idx}. {job['title']}\n"
                text_content += f"   📍 {job['location']}"
                if job.get('level'):
                    text_content += f" | 💼 {job['level']}"
                text_content += f"\n   📅 Veröffentlicht: {job['start_date']}\n"
                text_content += f"   🔗 Link: {job['url']}\n\n"
                
    text_content += "Dein Karriere-Job-Bot"
 
    msg = EmailMessage()
    subject_prefix = "[TEST] " if TEST_RUN else ""
    if total_jobs > 0:
        msg["Subject"] = f"{subject_prefix}Karriere-Ticker: {total_jobs} neue Stellen gefunden! 🎯"
    else:
        msg["Subject"] = f"{subject_prefix}Job-Ticker: Keine neuen Stellen in den letzten {DAYS_WINDOW} Tagen"
        
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    
    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype="html")
    
    try:
        print(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        # Security: Enforce certificate validation and secure settings using ssl context
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        # GDPR: Mask recipient email address in logs
        parts = TO_EMAIL.split("@")
        masked_to_email = f"{parts[0][:3]}...@{parts[1]}" if len(parts) == 2 else "recipient"
        print(f"Email successfully sent to {masked_to_email} at {datetime.now()}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        sys.exit(1)

# --- MAIN EXECUTION ---

def main():
    print(f"--- Combined Job Bot execution started at {datetime.now()} ---")
    print(f"Settings: DAYS_WINDOW={DAYS_WINDOW}, TEST_RUN={TEST_RUN}, SEND_EMPTY_REPORTS={SEND_EMPTY_REPORTS}")
    
    # Apply automatic retries for HTTP calls
    from urllib3.util import Retry
    from requests.adapters import HTTPAdapter
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    
    # Resource Management: using context manager to guarantee proper cleanup of connection pool
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        
        grouped_jobs = {}
        total_new_jobs = 0
        today = date.today()
        
        for scraper in SCRAPERS:
            print(f"Running scraper for {scraper.company_name}...")
            try:
                all_jobs = scraper.fetch_jobs(session)
                
                new_company_jobs = []
                for job in all_jobs:
                    # Security/Input Validation: Validate scraped URL schemes to prevent malicious javascript: redirects
                    job_url = job.get("url", "")
                    if not (job_url.startswith("http://") or job_url.startswith("https://")):
                        print(f"  [Security] Skipping job '{job.get('title')}' due to insecure URL scheme: '{job_url}'")
                        continue
                        
                    pub_date = parse_date(job.get("start_date"))
                    
                    if TEST_RUN:
                        new_company_jobs.append(job)
                    elif pub_date:
                        delta = (today - pub_date).days
                        if 0 <= delta <= DAYS_WINDOW:
                            new_company_jobs.append(job)
                            print(f"  Match: [NEW] {job['title']} (posted {delta} days ago, {job['start_date']})")
                    else:
                        print(f"  Warning: Skipping job '{job['title']}' due to unparseable date '{job.get('start_date')}'")
                        
                if new_company_jobs:
                    grouped_jobs[scraper.company_name] = new_company_jobs
                    total_new_jobs += len(new_company_jobs)
                    
            except Exception as e:
                print(f"Error executing scraper for {scraper.company_name}: {e}")
                
        print(f"Scraping complete. Total new jobs: {total_new_jobs}")
        for company, jobs in grouped_jobs.items():
            print(f"  - {company}: {len(jobs)} new jobs")
            
        if total_new_jobs > 0:
            print(f"Sending email notification with {total_new_jobs} jobs...")
            send_combined_email_alert(grouped_jobs)
        elif SEND_EMPTY_REPORTS:
            print("No new jobs found, but SEND_EMPTY_REPORTS is true. Sending report email...")
            send_combined_email_alert({})
        else:
            print("No new jobs found. Skipping email report.")
            
    print("--- Combined Job Bot execution completed successfully ---")

if __name__ == "__main__":
    main()
