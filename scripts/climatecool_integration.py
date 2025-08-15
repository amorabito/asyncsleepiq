import argparse
import asyncio
import getpass
import os

from asyncsleepiq import AsyncSleepIQ


async def main() -> None:
    """Simple script to exercise ClimateCool core climate APIs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--set",
        nargs=3,
        metavar=("SIDE", "MODE", "MINUTES"),
        help=(
            "Optionally set core climate for the first bed: "
            "<side> <mode> <minutes>"
        ),
    )
    args = parser.parse_args()

    username = os.getenv("SLEEPIQ_USERNAME") or input("SleepIQ username: ")
    password = os.getenv("SLEEPIQ_PASSWORD") or getpass.getpass("SleepIQ password: ")

    async with AsyncSleepIQ(username, password) as api:
        beds = await api.get_beds()
        if not beds:
            print("No beds found")
            return
        bed = beds[0]
        print(f"Using bed {bed.bed_id} ({bed.name})")

        if args.set:
            side, mode, minutes = args.set
            print(f"Setting {side} to {mode} for {minutes} minutes")
            await bed.set_core_climate(side=side, mode=mode, minutes=int(minutes))

        for side in ("left", "right"):
            try:
                state = await bed.get_core_climate(side)
                print(
                    f"{side}: mode={state.mode} remaining={state.remaining_minutes}"
                )
            except Exception as err:  # pragma: no cover - manual script
                print(f"{side}: error: {err}")


if __name__ == "__main__":
    asyncio.run(main())
