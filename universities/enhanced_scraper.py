import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import extruct
from price_parser import Price
import pycountry
import tldextract
from tenacity import retry, stop_after_attempt, wait_exponential

class EnhancedUniversityScraper:
    """Enhanced university scraper with improved data extraction patterns"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Enhanced patterns for better data extraction (English + Turkish)
        self.fee_patterns = {
            'tuition_domestic': [
                r'(?:domestic|local|home|resident|canadian|ontario|yerli|türk|turkish)\s+(?:students?\s+|öğrenci\s+)?(?:tuition|fees?|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:tuition|fees?|ücret|harç)\s+(?:for\s+|için\s+)?(?:domestic|local|home|resident|canadian|ontario|yerli|türk|turkish)\s+(?:students?\s*|öğrenci\s*)?:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:canadian|türk|turkish)\s+(?:citizens?|students?|vatandaş|öğrenci)\s*(?:tuition|fees?|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:ontario|türkiye)\s+(?:residents?|students?|vatandaş|öğrenci)\s*(?:tuition|fees?|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
            ],
            'tuition_international': [
                r'(?:international|foreign|overseas|non-resident|yabancı|uluslararası)\s+(?:students?\s+|öğrenci\s+)?(?:tuition|fees?|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:tuition|fees?|ücret|harç)\s+(?:for\s+|için\s+)?(?:international|foreign|overseas|non-resident|yabancı|uluslararası)\s+(?:students?\s*|öğrenci\s*)?:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:non-canadian|yabancı|uluslararası)\s+(?:students?\s+|öğrenci\s+)?(?:tuition|fees?|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
            ],
            'tuition_general': [
                r'(?:tuition|ücret|harç)\s+(?:and\s+|ve\s+)?(?:fees?|ücret|harç)?\s*:?\s*([£$€¥₹₺TL]\s*[\d,]+(?:\.\d{2})?)',
                r'(?:annual|yearly|yıllık)\s+(?:tuition|ücret|harç)\s*:?\s*([£$€¥₹₺TL]\s*[\d,]+(?:\.\d{2})?)',
                r'(?:program|bölüm)\s+(?:fee|ücret|harç)\s*:?\s*([£$€¥₹₺TL]\s*[\d,]+(?:\.\d{2})?)',
                r'eğitim\s+ücreti\s*:?\s*([£$€¥₹₺TL]\s*[\d,]+(?:\.\d{2})?)',
            ],
            'application': [
                r'(?:application|admission|processing|registration|başvuru|kayıt)\s+(?:fee|ücret|harç)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'başvuru\s+ücreti\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'kayıt\s+ücreti\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
            ],
            'deposit': [
                r'(?:tuition\s+|eğitim\s+)?(?:deposit|depozit|teminat)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:enrollment|kayıt)\s+(?:deposit|depozit|teminat)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:confirmation|onay)\s+(?:deposit|depozit|teminat)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
                r'(?:acceptance|kabul)\s+(?:deposit|depozit|teminat)\s*:?\s*([£$€¥₹₺TL\s]*[\d,]+(?:\.\d{2})?)',
            ]
        }
        
        self.intake_patterns = [
            r'(?:intake|admission|entry|başvuru|kayıt|kabul)\s+(?:dates?|periods?|times?|tarihleri|dönemleri)\s*:?\s*([^.]+)',
            r'(?:september|january|march|may|august|fall|spring|summer|winter|eylül|ocak|mart|mayıs|ağustos|güz|bahar|yaz|kış)\s+(?:intake|admission|entry|başvuru|kayıt|kabul)\s*(?:deadline|son\s+tarih)?\s*:?\s*([^.\n]*)',
            r'(?:applications?|başvurular)\s+(?:open|due|deadline|açık|son\s+tarih)\s*:?\s*([^.]+)',
            r'(?:semester|dönem)\s+(?:starts?|begins?|başlar|başlangıç)\s*:?\s*([^.]+)',
            r'(?:fall|autumn|güz)\s+(?:semester|term|dönem)\s*(?:deadline|due|son\s+tarih)?\s*:?\s*([^.\n]*)',
            r'(?:spring|winter|bahar|kış)\s+(?:semester|term|dönem)\s*(?:deadline|due|son\s+tarih)?\s*:?\s*([^.\n]*)',
            r'(?:summer|yaz)\s+(?:semester|term|dönem)\s*(?:deadline|due|son\s+tarih)?\s*:?\s*([^.\n]*)',
        ]
        
        self.deadline_patterns = [
            r'(?:application|admission)\s+deadline\s*:?\s*([^.]+)',
            r'apply\s+by\s*:?\s*([^.]+)',
            r'deadline\s*:?\s*([^.]+)',
            r'last\s+date\s+to\s+apply\s*:?\s*([^.]+)',
            r'deposit\s+(?:deadline|due)\s*:?\s*([^.]+)',
            r'acceptance\s+deadline\s*:?\s*([^.]+)',
            r'confirmation\s+deadline\s*:?\s*([^.]+)',
        ]
        
        self.deposit_patterns = [
            r'deposit\s+(?:due|deadline)\s*:?\s*([^.]+)',
            r'(?:tuition\s+)?deposit\s+must\s+be\s+paid\s+(?:by|before)\s*:?\s*([^.]+)',
            r'acceptance\s+deposit\s+due\s*:?\s*([^.]+)',
            r'enrollment\s+deposit\s+deadline\s*:?\s*([^.]+)',
        ]
        
        self.housing_patterns = [
            r'(?:campus|student|residence)\s+housing\s+(?:available|offered)',
            r'dormitor(?:y|ies)\s+(?:available|offered)',
            r'on-campus\s+accommodation',
            r'residential\s+(?:halls?|facilities)',
        ]
        
        self.visa_patterns = [
            r'(?:student\s+)?visa\s+(?:requirements?|information)',
            r'immigration\s+(?:requirements?|information)',
            r'f-1\s+visa',
            r'study\s+permit',
            r'tier\s+4\s+visa',
        ]
        
        self.scholarship_keywords = [
            'scholarship', 'grant', 'bursary', 'financial aid', 'funding',
            'merit award', 'need-based', 'tuition waiver', 'fellowship',
            'assistantship', 'stipend', 'work-study', 'fee waiver',
            'burs', 'destek', 'yardım', 'finansal', 'mali', 'kredi',
            'başarı', 'ödül', 'muafiyet', 'indirim'
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=1, max=4))
    def fetch_page(self, url):
        """Fetch page with retry logic"""
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response

    def extract_structured_data(self, soup, base_url):
        """Extract structured data from JSON-LD and microdata"""
        html = str(soup)
        structured_data = {}
        
        try:
            data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata'])
            
            # Process JSON-LD
            for item in data.get('json-ld', []):
                if isinstance(item, dict):
                    item_type = item.get('@type', '')
                    if any(t in str(item_type).lower() for t in ['university', 'college', 'educational']):
                        structured_data.update({
                            'name': item.get('name'),
                            'address': item.get('address'),
                            'telephone': item.get('telephone'),
                            'url': item.get('url'),
                            'description': item.get('description')
                        })
            
            # Process microdata
            for item in data.get('microdata', []):
                if isinstance(item, dict) and 'properties' in item:
                    props = item['properties']
                    if 'name' in props:
                        structured_data['name'] = props['name'][0] if props['name'] else None
                        
        except Exception as e:
            print(f"Error extracting structured data: {e}")
            
        return structured_data

    def extract_fees(self, text):
        """Enhanced fee extraction with domestic/international distinction and deposits"""
        fees = {
            'tuition_domestic': None,
            'tuition_international': None, 
            'tuition_general': None,
            'application_fee': None,
            'deposit_amount': None
        }
        
        for fee_type, patterns in self.fee_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    fee_text = match.group(1)
                    try:
                        price = Price.fromstring(fee_text)
                        if price and price.amount_float:
                            amount = float(price.amount_float)
                            
                            # Validate and assign based on fee type
                            if fee_type.startswith('tuition') and 500 <= amount <= 150000:
                                fees[fee_type] = amount
                            elif fee_type == 'application' and 0 <= amount <= 2000:
                                fees['application_fee'] = amount
                            elif fee_type == 'deposit' and 100 <= amount <= 50000:
                                fees['deposit_amount'] = amount
                                
                    except Exception:
                        numbers = re.findall(r'[\d,]+(?:\.\d{2})?', fee_text)
                        if numbers:
                            try:
                                amount = float(numbers[0].replace(',', ''))
                                if fee_type.startswith('tuition') and 500 <= amount <= 150000:
                                    fees[fee_type] = amount
                                elif fee_type == 'application' and 0 <= amount <= 2000:
                                    fees['application_fee'] = amount
                                elif fee_type == 'deposit' and 100 <= amount <= 50000:
                                    fees['deposit_amount'] = amount
                            except ValueError:
                                continue
        
        return fees

    def extract_intakes_and_deadlines(self, text):
        """Extract detailed intake periods with specific deadlines and deposit info"""
        intakes = []
        deposit_info = []
        
        # Enhanced intake extraction with deadline matching
        intake_seasons = {
            'fall': ['september', 'october', 'autumn'],
            'spring': ['january', 'february', 'march'],
            'summer': ['may', 'june', 'july'],
            'winter': ['december', 'january']
        }
        
        for season, months in intake_seasons.items():
            for pattern in self.intake_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    match_text = match.group(0).lower()
                    if season in match_text or any(month in match_text for month in months):
                        # Extract deadline if present
                        deadline = ''
                        if len(match.groups()) > 0 and match.group(1):
                            deadline = match.group(1).strip()[:100]
                        
                        intake_obj = {
                            'name': season.capitalize(),
                            'application_deadline': deadline,
                            'start_date': '',
                            'deposit_deadline': ''
                        }
                        
                        # Look for deposit deadline near this intake
                        for dep_pattern in self.deposit_patterns:
                            dep_matches = re.finditer(dep_pattern, text[max(0, match.start()-200):match.end()+200], re.IGNORECASE)
                            for dep_match in dep_matches:
                                if len(dep_match.groups()) > 0:
                                    intake_obj['deposit_deadline'] = dep_match.group(1).strip()[:100]
                                    break
                        
                        # Avoid duplicates
                        if not any(i['name'] == intake_obj['name'] for i in intakes):
                            intakes.append(intake_obj)
        
        # Extract general deposit information
        for pattern in self.deposit_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 0:
                    deposit_info.append(match.group(1).strip()[:150])
        
        return intakes[:6], deposit_info[:3]

    def extract_scholarships(self, soup, base_url):
        """Extract scholarship information from links and text"""
        scholarships = []
        
        # Find scholarship-related links
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link.get('href', '')
            
            if any(keyword in link_text for keyword in self.scholarship_keywords):
                scholarship_url = urljoin(base_url, href)
                scholarships.append({
                    'name': link.get_text(strip=True)[:100],
                    'coverage': '',
                    'eligibility': '',
                    'link': scholarship_url
                })
        
        # Look for scholarship sections in text
        text = soup.get_text()
        scholarship_sections = re.finditer(
            r'(scholarship|financial aid|funding).*?(?=\n\n|\.|scholarship|financial aid|funding|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        
        for match in scholarship_sections:
            section_text = match.group(0)[:200]
            if len(section_text) > 20:
                scholarships.append({
                    'name': 'General Scholarship Information',
                    'coverage': section_text,
                    'eligibility': '',
                    'link': base_url
                })
        
        return scholarships[:10]  # Limit results

    def extract_programs(self, soup, base_url):
        """Extract academic programs with better classification"""
        bachelor_programs = []
        masters_programs = []
        
        # Filter out navigation and irrelevant text
        excluded_terms = ['skip to', 'site map', 'campus map', 'site feedback', 'main content']
        
        # Look for program-specific elements
        for element in soup.find_all(['a', 'li', 'div', 'h3', 'h4']):
            text = element.get_text(strip=True)
            if len(text) < 5 or len(text) > 150:
                continue
                
            text_lower = text.lower()
            
            # Skip navigation and irrelevant elements
            if any(term in text_lower for term in excluded_terms):
                continue
                
            # Look for actual program names (English + Turkish)
            bachelor_terms = ['bachelor', 'undergraduate', 'bsc', 'ba', 'beng', 'lisans', 'ön lisans']
            master_terms = ['master', 'graduate', 'msc', 'ma', 'meng', 'phd', 'doctorate', 'yüksek lisans', 'doktora', 'master', 'tezli', 'tezsiz']
            
            if (any(term in text_lower for term in bachelor_terms) or
                any(term in text_lower for term in master_terms)):
                
                # Skip if it's just a generic link
                if text_lower in ['undergraduate programs', 'graduate programs', 'bachelor programs', 'master programs']:
                    continue
                    
                program_obj = {
                    'program_name': text,
                    'required_documents': [],
                    'language': 'English',
                    'duration_years': None,
                    'notes': ''
                }
                
                # Classify program level
                if any(term in text_lower for term in bachelor_terms):
                    program_obj['duration_years'] = 4  # Turkish universities typically 4 years
                    bachelor_programs.append(program_obj)
                elif any(term in text_lower for term in master_terms):
                    program_obj['duration_years'] = 2
                    program_obj['thesis_required'] = True
                    masters_programs.append(program_obj)
        
        # Remove duplicates and filter quality
        bachelor_programs = self._deduplicate_programs(bachelor_programs)
        masters_programs = self._deduplicate_programs(masters_programs)
        
        return bachelor_programs[:15], masters_programs[:15]

    def _deduplicate_programs(self, programs):
        """Remove duplicate programs based on name similarity"""
        unique_programs = []
        seen_names = set()
        
        for program in programs:
            name_key = program['program_name'].lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_programs.append(program)
        
        return unique_programs

    def extract_country_from_url(self, url):
        """Extract country from URL TLD or content"""
        try:
            extracted = tldextract.extract(url)
            domain = extracted.domain.lower()
            tld = extracted.suffix.split('.')[-1].upper()
            
            # Check domain names first
            if 'toronto' in domain or 'utoronto' in domain:
                return 'Canada'
            if 'harvard' in domain or 'mit' in domain or 'stanford' in domain:
                return 'United States'
            if 'oxford' in domain or 'cambridge' in domain:
                return 'United Kingdom'
            if 'istanbul' in domain or 'itu' in domain or 'bogazici' in domain:
                return 'Türkiye'
            
            # Common academic TLDs
            tld_country_map = {
                'EDU': 'United States',
                'AC': 'United Kingdom', 
                'UK': 'United Kingdom',
                'CA': 'Canada',
                'AU': 'Australia',
                'DE': 'Germany',
                'FR': 'France',
                'NL': 'Netherlands',
                'SE': 'Sweden',
                'DK': 'Denmark',
                'NO': 'Norway',
                'FI': 'Finland',
                'TR': 'Türkiye',
            }
            
            if tld in tld_country_map:
                return tld_country_map[tld]
            
            if len(tld) == 2:
                try:
                    country = pycountry.countries.get(alpha_2=tld)
                    return country.name if country else ''
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        return ''

    def find_application_links(self, soup, base_url):
        """Find application and admission links"""
        application_keywords = [
            'apply', 'application', 'admission', 'admissions', 'enroll', 'enrollment',
            'how to apply', 'apply now', 'apply online', 'start application'
        ]
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link.get('href', '').lower()
            
            if any(keyword in link_text or keyword in href for keyword in application_keywords):
                return urljoin(base_url, link['href'])
        
        return base_url

    def scrape_university(self, url):
        """Main scraping method with enhanced data extraction"""
        try:
            # Fetch main page
            response = self.fetch_page(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract structured data
            structured_data = self.extract_structured_data(soup, url)
            
            # Extract basic information
            name = (
                structured_data.get('name') or
                self._extract_title(soup) or
                urlparse(url).netloc
            )
            
            # Extract country and city
            country = self.extract_country_from_url(url)
            city = self._extract_city(soup, structured_data)
            
            # Get page text for analysis
            page_text = soup.get_text()
            
            # Extract fees
            fees = self.extract_fees(page_text)
            
            # Extract intakes and deposit info
            intakes, deposit_info = self.extract_intakes_and_deadlines(page_text)
            
            # Extract programs
            bachelor_programs, masters_programs = self.extract_programs(soup, url)
            
            # Extract scholarships
            scholarships = self.extract_scholarships(soup, url)
            
            # Find application link
            application_link = self.find_application_links(soup, url)
            
            # Extract description
            description = self._extract_description(soup)
            
            # Crawl additional pages for more data
            additional_data = self._crawl_additional_pages(soup, url)
            
            # Extract housing and visa information
            housing_info = self._extract_housing_info(soup, page_text)
            visa_info = self._extract_visa_info(soup, page_text)
            
            # Merge additional data
            if additional_data:
                fees.update(additional_data.get('fees', {}))
                intakes.extend(additional_data.get('intakes', []))
                deposit_info.extend(additional_data.get('deposit_info', []))
                scholarships.extend(additional_data.get('scholarships', []))
                bachelor_programs.extend(additional_data.get('bachelor_programs', []))
                masters_programs.extend(additional_data.get('masters_programs', []))
            
            # Compile final data with enhanced fee structure
            university_data = {
                'name': name,
                'country': country,
                'city': city,
                'course_offered': '',
                'tuition_fee_international': f"{fees.get('tuition_international') or 0:.2f}",
                'tuition_fee': f"{fees.get('tuition_general') or fees.get('tuition_international') or fees.get('tuition_domestic') or 0:.2f}",
                'application_fee': f"{fees.get('application_fee') or 0:.2f}",
                'deposit_amount': f"{fees.get('deposit_amount') or 0:.2f}",
                'deposit_deadlines': deposit_info[:3],
                'intakes': intakes[:6],
                'bachelor_programs': bachelor_programs[:25],
                'masters_programs': masters_programs[:25],
                'scholarships': scholarships[:15],
                'housing_info': housing_info,
                'visa_requirements': visa_info,
                'university_link': url,
                'application_link': application_link,
                'description': description,
                '_extraction_metadata': {
                    'extraction_date': datetime.now().isoformat(),
                    'pages_crawled': 1 + len(additional_data.get('crawled_urls', [])),
                    'confidence_score': self._calculate_confidence_score(fees, intakes, scholarships, bachelor_programs, masters_programs)
                }
            }
            
            return university_data
            
        except Exception as e:
            raise Exception(f"Failed to scrape {url}: {str(e)}")

    def _extract_title(self, soup):
        """Extract university name from various sources"""
        # Try meta tags first
        meta_title = soup.find('meta', property='og:site_name')
        if meta_title and meta_title.get('content'):
            return meta_title['content'].strip()
        
        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Try title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Clean up common title patterns
            title_text = re.sub(r'\s*[-|]\s*.*$', '', title_text)
            return title_text
        
        return ''

    def _extract_city(self, soup, structured_data):
        """Extract city from structured data or content"""
        # Try structured data first
        address = structured_data.get('address', {})
        if isinstance(address, dict):
            city = address.get('addressLocality') or address.get('addresslocality')
            if city:
                return city
        
        # Look for address patterns in text (English + Turkish)
        text = soup.get_text()
        
        # Check for Istanbul specifically
        if 'istanbul' in text.lower():
            return 'Istanbul'
        
        city_patterns = [
            r'(?:located in|based in|campus in|bulunduğu|yerleşke)\s+([A-Za-zçğıöşü\s]+)',
            r'(?:address|adres).*?([A-Za-zçğıöşü\s]+),\s*[A-Z]{2,}',
            r'([A-Za-zçğıöşü\s]+)\s+Üniversitesi',
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''

    def _extract_description(self, soup):
        """Extract university description"""
        # Try meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Look for about sections
        about_sections = soup.find_all(['div', 'section', 'p'], 
                                     string=re.compile(r'about|overview|mission', re.I))
        
        for section in about_sections:
            parent = section.parent if section.parent else section
            text = parent.get_text(strip=True)
            if 50 < len(text) < 500:
                return text
        
        return ''

    def _crawl_additional_pages(self, soup, base_url):
        """Crawl additional relevant pages for more data"""
        additional_data = {
            'fees': {},
            'intakes': [],
            'deposit_info': [],
            'scholarships': [],
            'bachelor_programs': [],
            'masters_programs': [],
            'crawled_urls': []
        }
        
        # Find relevant links to crawl with more specific patterns
        relevant_keywords = [
            'tuition', 'fees', 'cost', 'admission', 'admissions', 'apply',
            'international', 'domestic', 'canadian', 'deposit', 'deadline',
            'scholarship', 'financial-aid', 'housing', 'residence', 'visa'
        ]
        
        links_to_crawl = []
        priority_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            full_url = urljoin(base_url, link['href'])
            
            # Prioritize fee and admission pages
            if any(keyword in href or keyword in text for keyword in ['tuition', 'fees', 'cost', 'admission']):
                if full_url not in priority_links:
                    priority_links.append(full_url)
            elif any(keyword in href or keyword in text for keyword in relevant_keywords):
                if full_url not in links_to_crawl:
                    links_to_crawl.append(full_url)
        
        # Combine priority links first, then others
        links_to_crawl = priority_links[:3] + links_to_crawl[:5]
        
        # Crawl additional pages
        for url in links_to_crawl:
            try:
                response = self.fetch_page(url)
                page_soup = BeautifulSoup(response.text, 'html.parser')
                page_text = page_soup.get_text()
                
                # Extract additional fees
                page_fees = self.extract_fees(page_text)
                additional_data['fees'].update(page_fees)
                
                # Extract additional intakes
                page_intakes, page_deposits = self.extract_intakes_and_deadlines(page_text)
                additional_data['intakes'].extend(page_intakes)
                additional_data.setdefault('deposit_info', []).extend(page_deposits)
                
                # Extract additional scholarships
                page_scholarships = self.extract_scholarships(page_soup, url)
                additional_data['scholarships'].extend(page_scholarships)
                
                # Extract additional programs
                bachelor_progs, masters_progs = self.extract_programs(page_soup, url)
                additional_data['bachelor_programs'].extend(bachelor_progs)
                additional_data['masters_programs'].extend(masters_progs)
                
                additional_data['crawled_urls'].append(url)
                
            except Exception as e:
                print(f"Failed to crawl additional page {url}: {e}")
                continue
        
        return additional_data

    def _extract_housing_info(self, soup, text):
        """Extract campus housing and accommodation information"""
        housing_info = {
            'available': False,
            'types': [],
            'details': []
        }
        
        # Check for housing availability
        for pattern in self.housing_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                housing_info['available'] = True
                break
        
        # Extract housing types and details
        housing_keywords = ['dormitory', 'residence hall', 'apartment', 'housing', 'accommodation']
        for keyword in housing_keywords:
            matches = re.finditer(rf'{keyword}[^.]*', text, re.IGNORECASE)
            for match in matches:
                detail = match.group(0).strip()[:200]
                if len(detail) > 20 and detail not in housing_info['details']:
                    housing_info['details'].append(detail)
        
        # Look for housing links
        housing_links = []
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            if any(keyword in link_text for keyword in ['housing', 'residence', 'accommodation', 'dormitory']):
                housing_links.append({
                    'text': link.get_text(strip=True)[:100],
                    'url': link.get('href')
                })
        
        housing_info['links'] = housing_links[:5]
        return housing_info
    
    def _extract_visa_info(self, soup, text):
        """Extract student visa and immigration requirements"""
        visa_info = {
            'required': False,
            'types': [],
            'requirements': [],
            'links': []
        }
        
        # Check for visa requirements
        for pattern in self.visa_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                visa_info['required'] = True
                break
        
        # Extract visa types
        visa_types = ['f-1', 'j-1', 'tier 4', 'study permit', 'student visa']
        for visa_type in visa_types:
            if re.search(visa_type, text, re.IGNORECASE):
                visa_info['types'].append(visa_type.upper())
        
        # Extract requirements
        req_patterns = [
            r'(?:visa|immigration)\s+requirements?[^.]*',
            r'international\s+students?\s+must[^.]*',
            r'to\s+obtain\s+(?:a\s+)?(?:student\s+)?visa[^.]*'
        ]
        
        for pattern in req_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                requirement = match.group(0).strip()[:300]
                if len(requirement) > 30:
                    visa_info['requirements'].append(requirement)
        
        # Look for visa-related links
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            if any(keyword in link_text for keyword in ['visa', 'immigration', 'international student']):
                visa_info['links'].append({
                    'text': link.get_text(strip=True)[:100],
                    'url': link.get('href')
                })
        
        return visa_info
    
    def _calculate_confidence_score(self, fees, intakes, scholarships, bachelor_programs, masters_programs):
        """Calculate confidence score based on extracted data quality"""
        score = 0
        
        # Fee extraction (40 points max)
        if fees.get('tuition_domestic') or fees.get('tuition_international') or fees.get('tuition_general'):
            score += 20
        if fees.get('application_fee') is not None:
            score += 10
        if fees.get('deposit_amount'):
            score += 10
        
        # Intake information (20 points max)
        if intakes:
            score += min(len(intakes) * 4, 20)
        
        # Program information (25 points max)
        total_programs = len(bachelor_programs) + len(masters_programs)
        if total_programs > 0:
            score += min(total_programs * 2, 25)
        
        # Scholarship information (15 points max)
        if scholarships:
            score += min(len(scholarships) * 2, 15)
        
        return min(score, 100)