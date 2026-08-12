"""
Sample data collector.

Returns a static list of realistic Summer 2027 internship postings so the
dashboard is usable immediately, with no network access or API keys
required. This is the default source used by the "Refresh Jobs" button.

These are illustrative sample postings, not scraped from a live job board,
so there's no exact posting URL to link to. Each job's `url` points to the
company's real, verified careers/search page (see
src.config.COMPANY_CAREERS_URLS) rather than a guessed posting path --
guessed paths like ".../internships/software-engineering-2027" don't
actually exist and just 404. The UI marks these links "Needs Review" (see
src.urls.link_status) so it's clear they're a starting point, not a
confirmed live posting. A future real collector should set `url` to the
exact posting link it scrapes.
"""

from src.urls import get_company_careers_url

SOURCE_NAME = "sample_source"


def _job(company: str, title: str, location: str, description: str) -> dict:
    return {
        "company": company,
        "title": title,
        "location": location,
        "url": get_company_careers_url(company),
        "source": SOURCE_NAME,
        "description": description,
    }


def get_sample_jobs() -> list:
    """Return a list of sample internship job dicts."""
    jobs = [
        _job(
            "Capital One",
            "Software Engineering Intern - Summer 2027",
            "McLean, VA",
            "Join a backend engineering team building customer-facing "
            "financial applications. Work with Python, Java, and cloud "
            "infrastructure on AWS. Full-time offer eligible.",
        ),
        _job(
            "Microsoft",
            "AI Engineering Intern - Summer 2027",
            "Redmond, WA",
            "Work alongside applied AI teams building machine learning "
            "features for Microsoft products. Experience with Python, "
            "PyTorch, and large language models is a plus.",
        ),
        _job(
            "Palantir",
            "Machine Learning Intern",
            "New York, NY",
            "Build and evaluate machine learning models that power "
            "mission-critical data platforms for government and "
            "commercial partners. Python and data engineering skills "
            "required.",
        ),
        _job(
            "Booz Allen Hamilton",
            "Data Science Intern",
            "Arlington, VA",
            "Support federal clients with data analytics, dashboarding, "
            "and statistical modeling. Experience with Power BI, SQL, "
            "and Python preferred.",
        ),
        _job(
            "Leidos",
            "Cloud Engineering Intern",
            "Arlington, VA",
            "Support cloud migration and DevOps automation for federal "
            "systems using Azure and AWS. Exposure to infrastructure as "
            "code and CI/CD pipelines.",
        ),
        _job(
            "Northrop Grumman",
            "Cybersecurity Intern",
            "Washington, DC",
            "Assist the security operations team with vulnerability "
            "management, security dashboards, and Tenable-based "
            "reporting. Great fit for students with SOC or IT support "
            "experience.",
        ),
        _job(
            "Navy Federal Credit Union",
            "Backend Engineering Intern",
            "Vienna, VA",
            "Develop and maintain backend APIs and internal tools using "
            "Java and SQL. Collaborate with a Salesforce development "
            "team on internal applications.",
        ),
        _job(
            "Greystone",
            "Software Engineering Intern",
            "New York, NY",
            "Build internal tools and data pipelines supporting "
            "commercial real estate finance teams. Python, SQL, and "
            "automation experience valued.",
        ),
        _job(
            "Capital One",
            "Data Science Intern - Summer 2027",
            "Remote",
            "Analyze large datasets to support fraud detection and risk "
            "models. Python, pandas, and machine learning fundamentals "
            "required.",
        ),
        _job(
            "Microsoft",
            "Cloud Engineering Intern",
            "Redmond, WA",
            "Work on Azure infrastructure teams building internal "
            "developer tooling and automation for cloud services.",
        ),
        _job(
            "Booz Allen Hamilton",
            "Cybersecurity Intern - Summer 2027",
            "Washington, DC",
            "Support security operations and RPA-driven reporting "
            "automation for federal clients. IT support or cybersecurity "
            "dashboard experience preferred.",
        ),
        _job(
            "Leidos",
            "Backend Engineering Intern - Summer 2027",
            "Remote",
            "Build and maintain backend services and internal "
            "applications supporting large-scale federal data systems.",
        ),
        _job(
            "Palantir",
            "Software Engineering Intern - Summer 2027",
            "Washington, DC",
            "Full-stack engineering work on data integration platforms "
            "used by government and commercial partners. Python, "
            "TypeScript, and strong CS fundamentals expected.",
        ),
        _job(
            "Northrop Grumman",
            "AI Engineering Intern",
            "McLean, VA",
            "Support applied AI research for defense systems, including "
            "model evaluation, data labeling pipelines, and prototyping.",
        ),
    ]
    return jobs
