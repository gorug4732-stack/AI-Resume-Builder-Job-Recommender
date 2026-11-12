# AI Resume Builder & Live Job Recommendation

A command-line tool that collects your details through a short AI-driven chat, generates a professional PDF resume, and then searches the web for real, open job listings that match your profile.

## Features

- **Conversational data collection:** an AI assistant asks 15 questions one at a time (name, skills, projects, experience, preferred role, etc.) and validates the answers.
- **PDF resume generation:** builds a clean, formatted A4 resume using ReportLab.
- **Live job recommendations:** uses OpenAI's web search tool to find current openings on sites like Naukri, LinkedIn, Indeed, Glassdoor, Internshala and Foundit.
- **Match score:** each job comes with a match percentage, matching skills, missing skills and a short reason.

## How It Works

1. The script chats with you and collects your details as structured JSON.
2. It generates `Generated_Resume.pdf` from that data.
3. It sends your profile to an OpenAI model with web search enabled and returns the top 5 matching jobs, sorted by match percentage.

## Tech Stack

- Python 3.9+
- OpenAI API (`gpt-5-nano` for chat, `gpt-5-mini` with web search for jobs)
- ReportLab for PDF generation
- python-dotenv for environment variables

## Project Structure

```
.
├── main.py             # Main script
├── requirements.txt    # Python dependencies
├── .env                # Your API key (not committed)
├── .env.example        # Template for .env
├── .gitignore
└── README.md
```


**2. Create and activate a virtual environment (recommended)**

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Mac / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Add your API key**

Create a `.env` file in the project folder (same folder as `main.py`):

```
OPENAI_API_KEY=your_openai_api_key_here
```

No quotes and no spaces around `=`. You can copy `.env.example` as a starting point.

## Usage

```bash
python main.py
```

Answer the questions in the terminal. When all questions are done:

- `Generated_Resume.pdf` is saved in the project folder.
- The top job recommendations are printed in the terminal with apply links.

## Example Output

```
1. AI Engineer - Example Company (82% match)
   Location: Remote | Salary: N/A
   Why: Skills in Python and FastAPI match the requirements.
   Apply: https://...
```

## Notes

- Never commit your `.env` file or share your API key. If a key is exposed, revoke it from the OpenAI dashboard and create a new one.
- Web search is billed separately by OpenAI, so each run has a small extra cost.
- Job results come from live web search and may occasionally be outdated or incomplete. Always verify the listing before applying.
- Your OpenAI account must have access to the models set in `CHAT_MODEL` and `SEARCH_MODEL` in `main.py`.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `KeyError: 'OPENAI_API_KEY'` | `.env` is missing or not in the same folder as `main.py` |
| `401 Incorrect API key` | Key is wrong, has extra spaces/quotes, or was revoked. Create a new one |
| `ModuleNotFoundError` | Activate the virtual environment and run `pip install -r requirements.txt` |
| `'OpenAI' object has no attribute 'responses'` | Run `pip install -U openai` |

## Future Improvements

- Email the generated resume and job list
- Multiple resume templates
- Save and reload profiles so questions are not repeated
- Web UI using Streamlit or FastAPI

## License

This project is for learning and portfolio purposes. Add a license (for example MIT) if you plan to share it publicly.
