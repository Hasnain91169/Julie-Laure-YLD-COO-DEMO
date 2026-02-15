import argparse

from app.db import SessionLocal, init_db
from app.services.seed import seed_demo_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Friction Finder demo data")
    parser.add_argument("--count", type=int, default=24, help="Number of interviews to seed")
    parser.add_argument("--reset", action="store_true", help="Delete existing data before seeding")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as session:
        results = seed_demo_data(session, interview_count=max(20, args.count), reset=args.reset)

    print(f"Seed complete: {results}")


if __name__ == "__main__":
    main()
