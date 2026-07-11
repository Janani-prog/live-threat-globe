// Mirrors backend/app/ml/features.py ABUSEIPDB_CATEGORIES (AbuseIPDB's
// published category list: https://www.abuseipdb.com/categories).
const ABUSEIPDB_CATEGORIES: Record<string, string> = {
  "1": "DNS Compromise",
  "2": "DNS Poisoning",
  "3": "Fraud Orders",
  "4": "DDoS Attack",
  "5": "FTP Brute-Force",
  "6": "Ping of Death",
  "7": "Phishing",
  "8": "Fraud VoIP",
  "9": "Open Proxy",
  "10": "Web Spam",
  "11": "Email Spam",
  "12": "Blog Spam",
  "13": "VPN IP",
  "14": "Port Scan",
  "15": "Hacking",
  "16": "SQL Injection",
  "17": "Spoofing",
  "18": "Brute-Force",
  "19": "Bad Web Bot",
  "20": "Exploited Host",
  "21": "Web App Attack",
  "22": "SSH",
  "23": "IoT Targeted",
};

export function categoryLabel(id: string): string {
  return ABUSEIPDB_CATEGORIES[id] ?? `Category ${id}`;
}

export function parseCategories(category: string | null): string[] {
  if (!category) return [];
  return category
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean)
    .map(categoryLabel);
}
