"""Run an action without starting Streamlit: python -m assistant.cli /help."""
import sys
from dotenv import load_dotenv
from assistant.runtime import build_registry


def main():
    load_dotenv()
    text = ' '.join(sys.argv[1:])
    result = build_registry().execute(text)
    print(result if result is not None else 'Provide a command; use /help.')


if __name__ == '__main__':
    main()
