import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "startupconnect.db")

def add_sample_schemes():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if schemes already exist
    cur.execute("SELECT COUNT(*) FROM schemes")
    count = cur.fetchone()[0]
    
    if count == 0:
        schemes = [
            ("Startup India Seed Fund Scheme", "All", "Idea,Prototype", "Grant", 
             "Financial assistance to startups for proof of concept, prototype development, product trials, market entry and commercialization.",
             "DPIIT recognized startups incorporated within 2 years"),
            
            ("NIDHI-PRAYAS", "All", "Idea,Prototype", "Grant", 
             "Proof of concept grant up to Rs 10 lakhs for young innovators to translate their ideas into prototypes.",
             "Students, faculty, and startups in early stage"),
            
            ("Atal Innovation Mission", "EdTech,All", "Idea", "Incubation", 
             "Promotes innovation and entrepreneurship through Atal Tinkering Labs and incubation centers.",
             "Students and early-stage startups"),
            
            ("NABARD Startup Scheme", "AgriTech", "Prototype,MVP", "Loan", 
             "Financial support for agri-startups focusing on rural development and agriculture innovation.",
             "AgriTech startups with working prototype"),
            
            ("Credit Guarantee Scheme", "All", "MVP,Growth", "Guarantee", 
             "Collateral-free credit to startups through CGTMSE.",
             "Registered startups with business plan"),
            
            ("Stand-Up India", "All", "Growth", "Loan", 
             "Bank loans between Rs 10 lakh to Rs 1 crore for SC/ST and women entrepreneurs.",
             "Women and SC/ST entrepreneurs"),
            
            ("MSME Innovation Scheme", "All", "Prototype,MVP", "Grant", 
             "Support for innovative MSMEs in product development and commercialization.",
             "Registered MSMEs with innovative products"),
            
            ("Digital India Startup Hub", "EdTech,FinTech", "All", "Mentorship", 
             "Platform connecting startups with investors, mentors, and government schemes.",
             "All tech startups")
        ]
        
        cur.executemany("""
            INSERT INTO schemes (scheme_name, domain, stage, funding_type, description, eligibility)
            VALUES (?, ?, ?, ?, ?, ?)
        """, schemes)
        
        conn.commit()
        print(f"✅ Added {len(schemes)} government schemes to database")
    else:
        print(f"ℹ️ Database already has {count} schemes")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    add_sample_schemes()
