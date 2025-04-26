import sys
import os
import json
from run_all import run_stealth_agents, run_full_pipeline

def load_checkpoint(file):
    if os.path.exists(file):
        with open(file) as f:
            return set(json.load(f).get('processed', []))
    return set()

def save_checkpoint(file, processed):
    with open(file, 'w') as f:
        json.dump({'processed': list(processed)}, f)

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    symbols = [s.upper() for s in sys.argv[1:]]
    checkpoint_file = os.getenv('CHECKPOINT_FILE', 'checkpoint.json')
    processed = load_checkpoint(checkpoint_file)
    for symbol in symbols:
        if symbol in processed:
            print(f"Skipping {symbol}, already processed")
            continue
        run_stealth_agents(symbol)
        run_full_pipeline(symbol)
        processed.add(symbol)
        save_checkpoint(checkpoint_file, processed)
    print("✅ Batch run complete")

if __name__ == '__main__':
    main()
