import sys

sys.path.append("..")
from src import GlobalConfig
from src import ProcessPool
from src.Utils import postprocess_results, kill_all_terminals
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
    signal.signal(signal.SIGINT, partial(signal_handler, conf))

    s_time = time.time()
    p.run()

    postprocess_results(conf)

    elapsed_time = time.time() - s_time
    now = datetime.datetime.now()
    print("\n[{}] All done! Processing took {:.2f} secs".format(now.strftime("%Y-%m-%d %H:%M:%S"), elapsed_time))


if __name__ == "__main__":
    main()