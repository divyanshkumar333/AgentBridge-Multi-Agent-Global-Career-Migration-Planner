import os
import sqlite3
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "agentbridge.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create countries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        language TEXT NOT NULL,
        avg_tuition_annual_usd REAL NOT NULL,
        avg_living_annual_usd REAL NOT NULL,
        visa_type TEXT NOT NULL,
        visa_app_fee_usd REAL NOT NULL,
        health_insurance_usd REAL NOT NULL,
        first_year_setup_usd REAL NOT NULL,
        post_study_work_months INTEGER NOT NULL,
        language_barrier_level TEXT NOT NULL,
        risk_factors TEXT NOT NULL
    )
    """)
    
    # Create scholarships table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scholarships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sponsor TEXT NOT NULL,
        eligible_countries TEXT NOT NULL,
        degree_levels TEXT NOT NULL,
        award_amount_usd REAL NOT NULL,
        application_deadline TEXT NOT NULL,
        description TEXT NOT NULL,
        link TEXT NOT NULL
    )
    """)
    
    # Create careers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        demand_level TEXT NOT NULL,
        avg_salary_usd REAL NOT NULL,
        required_skills TEXT NOT NULL
    )
    """)
    
    # Check if data exists, if not, populate it
    countries_data = [
        ("US", "United States", "English", 45000.0, 24000.0, "F-1 Student Visa", 510.0, 2500.0, 3000.0, 12, "Low", 
         "High healthcare costs, intense job market competition, high tuition inflation, location-dependent safety profiles."),
        ("CA", "Canada", "English/French", 25000.0, 18000.0, "Study Permit", 150.0, 800.0, 2500.0, 36, "Low", 
         "Severe housing shortage in major cities, high cost of living in Vancouver/Toronto, long wait times for residency processing."),
        ("DE", "Germany", "German", 3000.0, 13200.0, "Student Visa", 80.0, 1400.0, 1500.0, 18, "High", 
         "High language barrier for day-to-day life and jobs, complex administrative bureaucracy, slower digitalization."),
        ("UK", "United Kingdom", "English", 28000.0, 18000.0, "Student Visa (Route)", 615.0, 1000.0, 2000.0, 24, "Low", 
         "Strict post-study salary thresholds for sponsorship, high living costs in London, uncertain policy shifts."),
        ("AU", "Australia", "English", 30000.0, 20000.0, "Student Visa (Subclass 500)", 430.0, 1500.0, 2500.0, 24, "Low", 
         "Isolated location, high rental costs in Sydney/Melbourne, strict cap on international student enrollments."),
        ("NL", "Netherlands", "Dutch/English", 18000.0, 16800.0, "Student Visa (MVV/VVR)", 230.0, 1200.0, 2000.0, 12, "Medium", 
         "Severe student housing crisis, high rental prices in major student cities, strict Binding Study Advice (BSA) thresholds."),
        ("IN", "India", "English/Hindi", 4000.0, 4800.0, "Domestic Employment", 0.0, 200.0, 500.0, 0, "Low", 
         "Intense local competition for roles, infrastructure growth pains, varying regional salary ranges."),
        ("JP", "Japan", "Japanese", 8000.0, 13200.0, "Student Visa (Specified Activities)", 30.0, 400.0, 1500.0, 12, "High", 
         "Strict Japanese language requirement (N3+), aging demographic labor shortages, traditional business work culture.")
    ]
    for row in countries_data:
        cursor.execute("SELECT COUNT(*) FROM countries WHERE code = ?", (row[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO countries (code, name, language, avg_tuition_annual_usd, avg_living_annual_usd, 
                                   visa_type, visa_app_fee_usd, health_insurance_usd, first_year_setup_usd, post_study_work_months, 
                                   language_barrier_level, risk_factors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
        
    scholarships_data = [
        ("Fulbright Foreign Student Program", "US Government", "Global", "Master, PhD", 45000.0, "Varies (Feb - Oct)", 
         "Full funding for tuition, airfare, living stipend, and health insurance for graduate study in the United States.",
         "https://foreign.fulbrightonline.org/"),
        ("DAAD Scholarship", "German Government", "Global", "Master, PhD", 15000.0, "Varies (Aug - Nov)", 
         "Stipend of 934-1,200 EUR monthly, travel allowance, health insurance, and tuition waivers for studies in Germany.",
         "https://www.daad.de/"),
        ("Chevening Scholarships", "UK Government", "Global", "Master", 38000.0, "November annually", 
         "Full funding including tuition fees, a monthly living allowance, return economy flights, and additional grants.",
         "https://www.chevening.org/"),
        ("Erasmus Mundus Joint Masters", "European Union", "Global", "Master", 24000.0, "January - March", 
         "Full scholarship covering tuition, travel, installation costs, and a monthly allowance of 1,000 EUR for study across EU countries.",
         "https://ec.europa.eu/programmes/erasmus-plus/opportunities/individuals/students/erasmus-mundus-joint-master-degrees_en"),
        ("Ontario Graduate Scholarship (OGS)", "Ontario Government", "Global", "Master, PhD", 11000.0, "Varies by University", 
         "Merit-based scholarship for international graduate students attending participating universities in Ontario, Canada.",
         "https://www.ontario.ca/page/ontario-graduate-scholarship"),
        ("Holland Scholarship", "Dutch Government", "Global", "Bachelor, Master", 5500.0, "Varies (Feb - May)", 
         "One-off grant of 5,000 EUR to help cover costs for international students entering their first year of study in the Netherlands.",
         "https://www.studyinnl.org/finances/holland-scholarship")
    ]
    for row in scholarships_data:
        cursor.execute("SELECT COUNT(*) FROM scholarships WHERE name = ?", (row[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO scholarships (name, sponsor, eligible_countries, degree_levels, award_amount_usd, 
                                      application_deadline, description, link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row)

    careers_data = [
        ("AI/ML Engineer", "High", 120000.0, "Python, PyTorch, Machine Learning, Deep Learning, SQL, Statistics"),
        ("Software Engineer", "High", 105000.0, "Java, Python, Javascript, React, Algorithms, System Design"),
        ("Data Scientist", "High", 110000.0, "Python, SQL, R, Machine Learning, Data Visualization, Tableau"),
        ("Cloud Architect", "High", 130000.0, "AWS, GCP, Azure, Docker, Kubernetes, Terraform, Networking"),
        ("Cybersecurity Specialist", "High", 115000.0, "Linux, Python, PenTesting, Cryptography, Security Audits, SIEM")
    ]
    for row in careers_data:
        cursor.execute("SELECT COUNT(*) FROM careers WHERE title = ?", (row[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO careers (title, demand_level, avg_salary_usd, required_skills)
            VALUES (?, ?, ?, ?)
            """, row)
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def get_countries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_country(code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries WHERE code = ?", (code.upper(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_scholarships(country_code=None, degree_level=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM scholarships WHERE 1=1"
    params = []
    
    if country_code:
        # Simple lookup: check if country_code or 'Global' is in eligible_countries
        query += " AND (eligible_countries LIKE ? OR eligible_countries = 'Global')"
        params.append(f"%{country_code}%")
        
    if degree_level:
        query += " AND degree_levels LIKE ?"
        params.append(f"%{degree_level}%")
        
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_careers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM careers")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
