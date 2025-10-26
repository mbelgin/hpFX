from bs4 import BeautifulSoup
import sys
import logging
import re


class HTMParser:
    def __init__(self, fn):
        self.__fn = fn
        try:
            with open(self.__fn) as input_htm:
                self.__soup = BeautifulSoup(input_htm, "lxml")
        except Exception as e:
            logging.error("Error: {} opening file: {}".format(e, self.__fn))
            sys.exit(1)

    def htm_to_csv(self):
        # First identify the type pf the report -- Single experiment or optimization
        report_type = self.__identify_report_type()
        if report_type == "Strategy Tester Report":
            # Some rows are in a clean "field1, val1, field2, val2,..." format, so no shifting needed
            results1 = self.__parse_experiment_report(extract_fields=["Symbol", "Total net profit", "Profit factor",
                                                                      "Maximal drawdown", "Total trades",
                                                                      "Total trades", "Profit trades", "Ticks modelled",
                                                                      "Mismatched charts errors"], shift_by=0)

            # Some rows have extra filed(s) at the beginning, "something, field1, val1, field2, val2,..."
            # so we shift by one
            results2 = self.__parse_experiment_report(extract_fields=["Maximum", "Profit trades (% of total)",
                                                                      "consecutive wins"], shift_by=1)
            results = {**results1, **results2}
            return self.__cleanup_results(results)
        elif report_type == "Optimization Report":
            return self.__parse_optimization_report()
        else:
            print(report_type)
            logging.error("Error parsing the HTM report")
            sys.exit(11)

    def __identify_report_type(self):
        report_type = self.__soup.find_all(text=["Strategy Tester Report", "Optimization Report"])
        # it's either one or the other
        if len(report_type) != 1:
            logging.error("Cannot identify the type of the provided HTM report")
            sys.exit(11)
        return report_type[0]

    def __parse_experiment_report(self, extract_fields, shift_by=0):
        soup = self.__soup
        extracted_fields = {}
        for row in soup.find_all("tr"):
            result = row.find("td", text=extract_fields)
            if result:
                cell = iter(row.find_all("td"))
                for _ in range(shift_by):
                    next(cell)
                for field, val in zip(cell, cell):
                    if field.text:
                        extracted_fields[field.text] = val.text
        return extracted_fields

    def __parse_optimization_report(self):
        soup = self.__soup
        result_lines = []
        all_results = []

        for row in soup.find_all("tr"):
            # Pair symbol is not provided on the standard row. Adding it manually so we know what results
            # belong to which pair when they are all concatenated on the single CSV report
            symbol_cell = row.find("td", text='Symbol')
            if symbol_cell:
                # VERY ugly way to extract the Symbol, can't think of another way
                symbol = str(row).split('>')[4].split()[0]

            # Parsing for these lines proved difficult. There are no keywords in values to match. These td lines differ
            # from others by having a title tough, which corresponds to the experiment inputs coming from the Expert
            # configuration(?!). Well, if it works it works. This is a hack, any format change will mess it up.
            result = row.find("td", title=True)
            if result:
                # First, extract the results line that's visible in the HTM report
                row_results = [symbol]
                for cell in row.find_all("td"):
                    row_results.append(cell.text)

                # Then extract the INPUT_## parameters that are not visible in the HTM report, but hidden in the source
                search_text = str(result)
                matched_entries = (re.findall('INPUT_.+?;', search_text))
                if len(matched_entries) > 0:
                    # Remove the semi colons from INPUT parameters
                    # matched_entries = [i.replace(';', '') for i in matched_entries]
                    for i in matched_entries:
                        row_results.append(i.replace(';', '').split('=')[1])
                # add the list representing a single experiment to the list of all results
                result_lines.append(row_results)

        headers = ['Pair', 'Pass', 'Profit', 'Total trades', 'Profit factor', 'Expected Payoff', 'Drawdown $',
                   'Drawdown %', 'OnTester result']

        headers += (['INPUT_{}'.format(i) for i in range(1, 26)])

        for rl in result_lines:
            all_results.append(dict(zip(headers, rl)))
        return all_results

    def __cleanup_results(self, results):
        """
        Post processing of the dictionary entries to provide the data
        in a format that matches the headers of the CSV file used to
        store test results.
        """
        # Trim the long pair name
        results['Symbol'] = results['Symbol'].split(' ')[0]

        # Split 'Maximal drawdown'
        tmp_val = results.pop('Maximal drawdown')
        results['Max DD'] = tmp_val.split(' ')[0]
        results['Max DD %'] = tmp_val.split('(')[1].split('%')[0]

        # Inject Recovery Factor, which is not normally not reported by MT4
        # Recovery Factor = Net Profit / Max Drawdown

        if round(float(results['Max DD']), 2) == 0.0:
            results['Recov factor'] = "n/a"
        else:
            results['Recov factor'] = round(float(results['Total net profit']) / float(results['Max DD']), 2)

        # Split 'Short positions (won %)'
        tmp_val = results.pop('Short positions (won %)')
        results['short trades'] = tmp_val.split(' ')[0]
        results['short won %'] = tmp_val.split('(')[1].split('%')[0]

        # Split 'Long positions (won %)'
        tmp_val = results.pop('Long positions (won %)')
        results['long trades'] = tmp_val.split(' ')[0]
        results['long won %'] = tmp_val.split('(')[1].split('%')[0]

        # Split 'Profit trades (% of total)'
        tmp_val = results.pop('Profit trades (% of total)')
        results['Profit trades'] = tmp_val.split(' ')[0]
        results['Profit trades %'] = tmp_val.split('(')[1].split('%')[0]

        # Split 'Loss trades (% of total)'
        tmp_val = results.pop('Loss trades (% of total)')
        results['Loss trades'] = tmp_val.split(' ')[0]
        results['Loss trades %'] = tmp_val.split('(')[1].split('%')[0]

        # Rename 'consecutive wins'
        results['Avg cons wins'] = results.pop('consecutive wins')

        # Rename 'consecutive losses'
        results['Avg cons losses'] = results.pop('consecutive losses')

        # Remove 'consecutive wins (profit in money)'
        results.pop('consecutive wins (profit in money)')

        # Remove 'consecutive losses (loss in money)'
        results.pop('consecutive losses (loss in money)')

        # Remove Relative drawdown
        results.pop('Relative drawdown')

        # Rename 'Bars in test'
        results['Bars'] = results.pop('Bars in test')

        # Rename 'Ticks modelled'
        results['Ticks'] = results.pop('Ticks modelled')

        # Rename 'Mismatched charts errors'
        results['Chart Err'] = results.pop('Mismatched charts errors')

        # Rename 'Modelling quality'
        results['ModelQual'] = results.pop('Modelling quality')

        # Returning the dictionary in list format to keep the return type of htm_to_csv consistent
        return_list = [results]
        return return_list
