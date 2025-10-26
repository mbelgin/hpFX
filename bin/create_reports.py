from src import GlobalConfig
import argparse
from src import HTMParser
from src.Utils import dict_to_csv
import glob
import os

# Sample run: C:\Users\User\Documents\Programming\hpFX>python create_reports.py -d "C:\\Users\\User\\Documents\\hpFX_Shared\\tester\\f\\STANDALONE_RUNS\\___OPTIMIZATION_WINNING_MACD-4H-V10_b1x0+STOCHASTICRVI_b1xb2\\20160101-20200101\
# \htm_reports"

# Missing:
# NZDCHF
# USDCAD
# USDJPY
# EURCAD
# USDJPY


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", type=str, help="Absolute path to the directory that includes HTM files")
    args = parser.parse_args()
    htm_dir = args.directory
    # not needed so far... conf = GlobalConfig()

    output_csv = os.path.join(htm_dir, "MERGED_RESULTS.csv")
    htm_search_key = htm_dir + "\\*.htm"
    htm_files = glob.glob(htm_search_key)

    # print(htm_files)

    for h in htm_files:
        print("Processing: {}".format(h))
        parsed_results = HTMParser(h)
        test_output = parsed_results.htm_to_csv()
        dict_to_csv(test_output, output_csv)

    print("Results are written on: ", output_csv)


if __name__ == "__main__":
    main()

