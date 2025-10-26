import sys
sys.path.append("..")
from src import GlobalConfig
from src import ProcessPool
from src import HTMParser
from src.Utils import dict_to_csv, kill_all_terminals
from functools import partial
import time
import logging
import signal
import datetime

def signal_handler(conf, sig, frame):
    if input("Are you sure you'd like to terminate all tests and exit? (y/n)").upper() == "Y":
        kill_all_terminals(conf)
        sys.exit(0)
    else:
        return


#  #!/usr/bin/env python
#  import signal
#  import sys
#
#  def signal_handler(sig, frame):
#      print('You pressed Ctrl+C!')
#      sys.exit(0)
#  signal.signal(signal.SIGINT, signal_handler)
#  print('Press Ctrl+C')
#  signal.pause()


def main():
    conf = GlobalConfig()
    conf.ingest_args()
    conf.prepare_test_environment()
    p = ProcessPool(conf)
    # CTRL+C Handler -- Not perfect but close enough.
    signal.signal(signal.SIGINT, partial(signal_handler, conf))
    s_time = time.time()
    p.run()

    for s in conf.symbols:
        if s in conf.htm_reports.keys():
            html_report = conf.htm_reports[s]
            parsed_results = HTMParser(html_report)
            test_output = parsed_results.htm_to_csv()
            dict_to_csv(test_output, conf.test_report_csv)
        else:
            logging.warning("Missing the HTM report for {}".format(s))

    trg_csv = conf.abs_test_specific_folder

    elapsed_time = time.time() - s_time
    now = datetime.datetime.now()

    print("\n[{}] All done! Processing took {:.2f} secs".format(now.strftime("%Y-%m-%d %H:%M:%S"), elapsed_time))


if __name__ == "__main__":
    main()
