import argparse
import contextlib
import csv
import io
import itertools
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

from config import *
from game_stats import COLUMNS as STAT_COLUMNS
from main import load_agent_class
from tournament import World

RESULT_FIELDS = (["blue", "red", "seed", "winner", "reason", "ticks", "first_contact_tick", "blue_errors", "red_errors"]
                 + STAT_COLUMNS)


def play_match(match):
    """Plays one headless game and returns its result. Agent output is suppressed."""
    blue_folder, red_folder, seed = match
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        world = World(HEIGHT, WIDTH, load_agent_class(blue_folder, "blue_agent"),
                      load_agent_class(red_folder, "red_agent"), seed=seed)
        world.generate_world()
        while not world.win:
            world.step()
        world.terminate_agents()

    winner, reason = world.win
    return {
        "blue": team_name(blue_folder),
        "red": team_name(red_folder),
        "seed": seed,
        "winner": winner,
        "reason": reason,
        "ticks": world.tick,
        "first_contact_tick": world.stats.first_contact_tick,
        "blue_errors": world.error_counts["blue"],
        "red_errors": world.error_counts["red"],
        **world.stats.as_row(),
    }


def team_name(folder):
    return os.path.basename(os.path.normpath(folder))


def schedule(folders, rounds, first_seed):
    """Every team plays every other team on the same maps, once on each side."""
    seeds = range(first_seed, first_seed + rounds)
    return [(blue, red, seed) for blue, red in itertools.permutations(folders, 2) for seed in seeds]


def play_all(matches, workers):
    results = []
    report_every = max(1, len(matches) // 100)
    with Pool(workers) as pool:
        for result in pool.imap_unordered(play_match, matches):
            results.append(result)
            if len(results) % report_every == 0 or len(results) == len(matches):
                print(f"\rPlayed {len(results)}/{len(matches)} games", end="", file=sys.stderr)
    print(file=sys.stderr)
    return sorted(results, key=lambda r: (r["blue"], r["red"], r["seed"]))


def save_results(results, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)


def tally(results):
    """Returns {(team, opponent): [wins, ties, losses]} from the team's point of view."""
    records = defaultdict(lambda: [0, 0, 0])
    for r in results:
        for color, team, opponent in (("blue", r["blue"], r["red"]), ("red", r["red"], r["blue"])):
            outcome = 0 if r["winner"] == color else 1 if r["winner"] == "tied" else 2
            records[team, opponent][outcome] += 1
    return records


def score(wins, ties, losses):
    return 100 * (wins + 0.5 * ties) / (wins + ties + losses)


def print_standings(results):
    records = tally(results)
    teams = sorted({r["blue"] for r in results})
    totals = {t: [sum(records[t, o][i] for o in teams if o != t) for i in range(3)] for t in teams}
    errors = {t: sum(r["blue_errors"] for r in results if r["blue"] == t)
                 + sum(r["red_errors"] for r in results if r["red"] == t) for t in teams}
    ranking = sorted(teams, key=lambda t: -score(*totals[t]))

    width = max(len(t) for t in teams) + 2
    print("\nStandings (score: win = 1, tie = 0.5)")
    print(f"{'team':<{width}}{'score':>7}{'wins':>7}{'ties':>7}{'losses':>8}{'errors':>8}")
    for t in ranking:
        wins, ties, losses = totals[t]
        print(f"{t:<{width}}{score(*totals[t]):>6.1f}%{wins:>7}{ties:>7}{losses:>8}{errors[t]:>8}")

    print("\nScore of row team against column team (%)")
    print(" " * width + "".join(f"{t[:8]:>9}" for t in ranking))
    for t in ranking:
        cells = "".join(f"{'-':>9}" if o == t else f"{score(*records[t, o]):>9.0f}" for o in ranking)
        print(f"{t:<{width}}{cells}")

    reasons = defaultdict(int)
    for r in results:
        reasons[r["reason"]] += 1
    print("\nGame endings: " + ", ".join(f"{reason} {count}" for reason, count in sorted(reasons.items())))


def main():
    parser = argparse.ArgumentParser(description="Round-robin tournament between agent folders")
    parser.add_argument("teams", nargs="+", help="Folders containing an agent.py")
    parser.add_argument("--rounds", type=int, default=10, help="Maps per pairing; each map is played once from each side")
    parser.add_argument("--seed", type=int, default=0, help="Seed of the first map")
    parser.add_argument("--workers", type=int, default=None, help="Parallel processes (default: all CPU cores)")
    parser.add_argument("--output", default="tournament_results.csv", help="CSV file for per-game results")
    args = parser.parse_args()

    names = [team_name(folder) for folder in args.teams]
    if len(set(names)) != len(names):
        parser.error("team folders must have distinct names")
    if len(names) < 2:
        parser.error("at least two teams are needed")

    results = play_all(schedule(args.teams, args.rounds, args.seed), args.workers)
    save_results(results, args.output)
    print_standings(results)
    print(f"\nPer-game results saved to {args.output}")


if __name__ == "__main__":
    main()
