import re
from typing import List, Optional
from python.db.models import Job
import json
from pathlib import Path

# Load candidate preferences (willing_to_relocate) once at import time
_WILLING_TO_RELOCATE = False
try:
    resume_path = Path("data/resume.json")
    if not resume_path.exists():
        resume_path = Path(__file__).resolve().parent.parent / "data" / "resume.json"
    if resume_path.exists():
        data = json.loads(resume_path.read_text(encoding="utf-8"))
        _WILLING_TO_RELOCATE = bool(data.get("willing_to_relocate", False))
except Exception:
    _WILLING_TO_RELOCATE = False

# Roles to reject explicitly (seniority, leadership, non-SWE disciplines, non-tech)
BLOCKED_ROLES = [
    # Seniority & Leadership
    r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\btech lead\b", r"\bteam lead\b",
    r"\bprincipal\b", r"\bstaff\b", r"\barchitect\b", r"\bdistinguished\b",
    r"\bfellow\b", r"\bfellowship\b", r"\bmanager\b", r"\bmanagement\b", r"\bmgr\b",
    r"\bdirector\b", r"\bvp\b", r"\bvice president\b", r"\bhead of\b", r"\bhead\b",
    r"\bchief\b", r"\bpartner\b", r"\bengineering leader\b",
    
    # Irrelevant engineering disciplines (Hardware, Electrical, Silicon, Mechanical, Embedded)
    r"\belectrical\b", r"\bhardware\b", r"\belectronics\b", r"\bpcba\b", r"\bcircuit\b",
    r"\bmechanical\b", r"\bthermal\b", r"\boptical\b", r"\boptics\b", r"\bmaterials\b",
    r"\bsilicon\b", r"\basic\b", r"\bfpga\b", r"\bsemiconductor\b", r"\bwafer\b",
    r"\briscv\b", r"\bemulation\b", r"\bfirmware\b", r"\bembedded\b",
    r"\btechnician\b", r"\bmachinist\b", r"\baudio\b", r"\bvideo engineer\b", r"\bav engineer\b",
    
    # Irrelevant non-engineering disciplines
    r"\brecruiter\b", r"\brecruiting\b", r"\btalent\b", r"\bhuman resources\b", r"\bhr\b",
    r"\bsales\b", r"\baccount executive\b", r"\bbusiness development\b", r"\bsdr\b", r"\bbdr\b",
    r"\bmarketing\b", r"\bproduct manager\b", r"\bproduct management\b", r"\bevangelist\b",
    r"\bdeveloper relations\b", r"\bdevrel\b", r"\badvocate\b",
    r"\bdesigner\b", r"\bdesign\b", r"\bui/ux\b", r"\bgraphic\b", r"\bcreative\b",
    r"\blegal\b", r"\bcounsel\b", r"\bcompliance\b", r"\bregulatory\b",
    r"\btax\b", r"\baccounting\b", r"\baudit\b", r"\bfacilit(y|ies)\b", r"\bworkplace\b",
    r"\bcapital markets\b", r"\bfinance and strategy\b", r"\bstrategic finance\b",
    
    # Excluded SWE subdomains per GEMINI.md
    r"\bfrontend\b", r"\bfront-end\b", r"\breact developer\b", r"\bui developer\b",
    r"\bqa\b", r"\bquality assurance\b",
]

# Roles to accept (target software, backend, data, AI/ML, platform, infra)
ALLOWED_ROLES = [
    r"software", r"developer", r"backend", r"fullstack", r"full-stack", r"full stack",
    r"data engineer", r"data platform", r"data scientist", r"data science", r"data analyst",
    r"analytics engineer", r"machine learning", r"\bml engineer\b", r"applied ai", r"\bai engineer\b",
    r"\bai developer\b", r"devops", r"platform engineer", r"infrastructure", r"cloud engineer",
    r"python", r"forward deployed"
]

# Non-US and Non-India locations / foreign remotes to strictly block
INTL_REJECT_REGEX = re.compile(
    r"\b("
    r"uk|united kingdom|london|england|scotland|ireland|dublin(?!\s*,\s*(?:oh|ohio|ca|california))|"
    r"canada|toronto|vancouver|montreal|ottawa|calgary|alberta|ontario|quebec|british columbia|"
    r"germany|berlin|munich|frankfurt|dresden|hamburg|"
    r"france|paris|spain|madrid|barcelona|italy|milan|rome|"
    r"netherlands|amsterdam|brazil|são paulo|sao paulo|"
    r"mexico|mexico city|guadalajara|monterrey|"
    r"australia|sydney|melbourne|singapore|"
    r"japan|tokyo|osaka|korea|seoul|china|beijing|shanghai|shenzhen|"
    r"taiwan|taipei|denmark|copenhagen|herlev|sweden|stockholm|"
    r"switzerland|zurich|zrich|geneva|poland|warsaw|krakow|israel|tel aviv|"
    r"portugal|lisbon|porto|hungary|budapest|austria|vienna|belgium|brussels|"
    r"norway|oslo|finland|helsinki|espoo|czech|prague|"
    r"uae|dubai|abu dhabi|hong kong|argentina|buenos aires|uruguay|montevideo|"
    r"chile|colombia|bogota|costa rica|philippines|manila|malaysia|penang|"
    r"kuala lumpur|serbia|belgrade|emea|apac|latam|europe"
    r")\b",
    re.IGNORECASE
)

# Explicit US or India locations (cities, country names, or explicit US Remote designations)
US_EXPLICIT_OR_INDIA_REGEX = re.compile(
    r"\b("
    # India
    r"india|bangalore|bengaluru|hyderabad|chennai|pune|mumbai|delhi|noida|gurgaon|gurugram|ahmedabad|"
    # US generic & US-based remote
    r"united states|usa?|u\.s\.a?|remote\s*-\s*us(a)?|remote:\s*united states|us\s*-\s*remote|"
    r"us remote|remote,\s*us(a)?|remote\s*\(us\)|remote\s*\(united states\)|remote-friendly,\s*united states|"
    # US tech hubs / major cities
    r"san francisco|sf\b|nyc?\b|new york|seattle|austin|chicago|boston|los angeles|la\b|"
    r"san jose|sunnyvale|mountain view|palo alto|menlo park|redwood|santa clara|fremont|oakland|"
    r"san diego|sacramento|torrance|culver city|irvine|pasadena|berkeley|san mateo|"
    r"denver|boulder|salt lake city|phoenix|scottsdale|tempe|chandler|mesa|arizona|"
    r"atlanta|miami|orlando|tampa|raleigh|durham|charlotte|nashville|dallas|houston|"
    r"pittsburgh|philadelphia|baltimore|washington|dc\b|d\.c\.|cambridge|waltham"
    r")\b",
    re.IGNORECASE
)

# Additional US state names and abbreviations (only checked when no foreign country is in the location string)
US_STATES_REGEX = re.compile(
    r"\b("
    r"california|texas|new york|washington|colorado|massachusetts|illinois|florida|"
    r"georgia|north carolina|ohio|michigan|virginia|pennsylvania|utah|oregon|portland|"
    r"ca|ny|tx|wa|il|ma|co|az|ga|fl|nc|va|pa|ut|oh|mi|nj|md|mn|mo|tn|in|wi"
    r")\b",
    re.IGNORECASE
)


def passes_job_filter(job: Job) -> bool:
    """
    Evaluates a job against role and location criteria.
    Returns True if it's a junior/mid-level software/data job in the US or India.
    """
    title = job.title.lower()
    location = str(job.location).lower() if job.location else ""
    
    # 1. Check blocked roles (leadership, non-software disciplines, non-tech)
    for block_pattern in BLOCKED_ROLES:
        if re.search(block_pattern, title):
            return False
            
    # 2. Check allowed roles (must match target software/data/cloud/infra profile)
    role_match = False
    for allow_pattern in ALLOWED_ROLES:
        if re.search(allow_pattern, title):
            role_match = True
            break
            
    if not role_match:
        return False

    # 3. Check location: strictly US (in-person, hybrid, or US-Remote) or India
    is_foreign = bool(INTL_REJECT_REGEX.search(location))
    has_explicit_us_or_india = bool(US_EXPLICIT_OR_INDIA_REGEX.search(location))

    # If location mentions a foreign country, ONLY accept if it explicitly includes a US or India option
    if is_foreign:
        return has_explicit_us_or_india

    # If no foreign country mentioned, check for US/India tech hubs or state indicators
    if has_explicit_us_or_india or bool(US_STATES_REGEX.search(location)):
        return True

    # If flagged remote (or location text contains remote) and is NOT a foreign country -> accept
    if job.remote or "remote" in location or "anywhere" in location:
        return True

    # If unclear location without US or India indicators, drop it
    return False
