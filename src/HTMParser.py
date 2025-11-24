from bs4 import BeautifulSoup
import sys
import logging
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


class HTMParser:
    def __init__(self, fn):
        self.__fn = fn
        try:
            with open(self.__fn) as input_htm:
                self.__soup = BeautifulSoup(input_htm, "lxml")
        except Exception as e:
            logging.error("Error: {} opening file: {}".format(e, self.__fn))
            sys.exit(1)

    def htm_to_csv(self, calculate_sharpe=False, risk_free_rate=0.0, date_from=None, date_to=None):
        """
        Parse HTM report and return both summary results and individual trades.

        Args:
            calculate_sharpe: Boolean to enable Sharpe Ratio calculation
            risk_free_rate: Annual risk-free rate as decimal (e.g., 0.02 for 2%)
            date_from: Test start date as string 'YYYY.MM.DD'
            date_to: Test end date as string 'YYYY.MM.DD'

        Returns:
            tuple: (summary_results_list, trades_list)
                - summary_results_list: List with single dict of summary metrics
                - trades_list: List of dicts, one per trade row
        """
        # First identify the type of the report -- Single experiment or optimization
        report_type = self.__identify_report_type()
        if report_type == "Strategy Tester Report":
            # Some rows are in a clean "field1, val1, field2, val2,..." format, so no shifting needed
            results1 = self.__parse_experiment_report(extract_fields=["Symbol", "Total net profit", "Profit factor",
                                                                      "Maximal drawdown", "Total trades",
                                                                      "Total trades", "Profit trades", "Ticks modelled",
                                                                      "Mismatched charts errors"], shift_by=0)

            # Some rows have extra field(s) at the beginning, "something, field1, val1, field2, val2,..."
            # so we shift by one
            results2 = self.__parse_experiment_report(extract_fields=["Maximum", "Profit trades (% of total)",
                                                                      "consecutive wins"], shift_by=1)
            results = {**results1, **results2}
            results = self.__cleanup_results(results)

            # Extract individual trades
            trades = self.__extract_trades(results[0]['Symbol'])

            # Calculate Sharpe Ratios if enabled
            if calculate_sharpe and len(trades) > 0:
                sharpe_results = self.calculate_sharpe_ratio(trades, risk_free_rate, date_from, date_to)
                results[0]['Shrp(A-mo)'] = sharpe_results['monthly']
                results[0]['Shrp(Yr)'] = sharpe_results['annual']
            else:
                results[0]['Shrp(A-mo)'] = 'N/A'
                results[0]['Shrp(Yr)'] = 'N/A'

            return results, trades

        elif report_type == "Optimization Report":
            optimization_results = self.__parse_optimization_report()
            # Optimization reports don't have individual trades, return empty list
            return optimization_results, []
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

    def __extract_trades(self, symbol):
        """
        Extract all individual trades from the HTM report table.
        Returns a list of dicts, one per row (includes both entry and exit rows).

        Structure mirrors HTM table:
        Symbol, #, Time, Type, Order, Size, Price, S/L, T/P, Profit, Balance, Return %
        """
        soup = self.__soup
        trades = []

        # Find the trade table - it's the one with header row containing "Time", "Type", "Order"
        tables = soup.find_all("table")
        trade_table = None
        for table in tables:
            header_row = table.find("tr", bgcolor="#C0C0C0")
            if header_row:
                cells = header_row.find_all("td")
                headers = [cell.text.strip() for cell in cells]
                if "Time" in headers and "Type" in headers and "Order" in headers:
                    trade_table = table
                    break

        if not trade_table:
            logging.warning("Could not find trade table in HTM report for {}".format(symbol))
            return []

        # Get initial deposit for first trade return calculation
        initial_deposit = self.__get_initial_deposit()
        previous_balance = initial_deposit

        # Parse all trade rows (skip header row)
        rows = trade_table.find_all("tr")
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("td")
            if len(cells) < 8:  # Minimum required columns
                continue

            # Extract data from cells
            row_num = cells[0].text.strip()
            time = cells[1].text.strip()
            trade_type = cells[2].text.strip()
            order = cells[3].text.strip()
            size = cells[4].text.strip()
            price = cells[5].text.strip()
            sl = cells[6].text.strip()
            tp = cells[7].text.strip()

            # Profit and Balance may be empty for entry rows
            profit = ""
            balance = ""
            return_pct = ""

            if len(cells) >= 10:
                profit = cells[8].text.strip()
                balance = cells[9].text.strip()

                # Calculate return % for close rows (those with profit/balance)
                if profit and balance:
                    try:
                        profit_val = float(profit)
                        balance_val = float(balance)
                        # Return % = (Profit / Balance_before_trade) * 100
                        return_pct = round((profit_val / previous_balance) * 100, 4)
                        previous_balance = balance_val
                    except ValueError:
                        return_pct = ""

            trade_dict = {
                'Symbol': symbol,
                '#': row_num,
                'Time': time,
                'Type': trade_type,
                'Order': order,
                'Size': size,
                'Price': price,
                'S/L': sl,
                'T/P': tp,
                'Profit': profit,
                'Balance': balance,
                'Return %': return_pct
            }
            trades.append(trade_dict)

        return trades

    def __get_initial_deposit(self):
        """Extract initial deposit from HTM report."""
        soup = self.__soup
        for row in soup.find_all("tr"):
            cell = row.find("td", text="Initial deposit")
            if cell:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    try:
                        return float(cells[1].text.strip())
                    except ValueError:
                        pass
        # Default to 10000 if not found
        logging.warning("Could not find initial deposit in HTM, defaulting to 10000")
        return 10000.0

    def calculate_sharpe_ratio(self, trades, risk_free_rate, date_from, date_to):
        """
        Calculate Monthly and Annual Sharpe Ratios from trade data.

        Args:
            trades: List of trade dicts with 'Time', 'Return %', etc.
            risk_free_rate: Annual risk-free rate as decimal
            date_from: Test start date as string 'YYYY.MM.DD'
            date_to: Test end date as string 'YYYY.MM.DD'

        Returns:
            dict: {'monthly': value or 'N/A', 'annual': value or 'N/A'}
        """
        try:
            # Filter to only closed trades (those with Return %)
            closed_trades = [t for t in trades if t['Return %'] != '']

            if len(closed_trades) == 0:
                logging.warning("No closed trades found for Sharpe calculation")
                return {'monthly': 'N/A', 'annual': 'N/A'}

            # Parse date range
            try:
                start_date = datetime.strptime(date_from, '%Y.%m.%d')
                end_date = datetime.strptime(date_to, '%Y.%m.%d')
            except:
                logging.warning("Could not parse date range for Sharpe calculation")
                return {'monthly': 'N/A', 'annual': 'N/A'}

            # Calculate test duration in years
            duration_days = (end_date - start_date).days
            duration_years = duration_days / 365.25

            # Monthly Sharpe Ratio
            monthly_sharpe = self.__calculate_period_sharpe(
                closed_trades, risk_free_rate, 'monthly', start_date, end_date
            )

            # Annual Sharpe Ratio - only if test period >= 1 year
            if duration_years >= 1.0:
                annual_sharpe = self.__calculate_period_sharpe(
                    closed_trades, risk_free_rate, 'annual', start_date, end_date
                )
            else:
                annual_sharpe = 'N/A'
                logging.warning("Test period < 1 year, Annual Sharpe not calculated")

            return {'monthly': monthly_sharpe, 'annual': annual_sharpe}

        except Exception as e:
            logging.error("Error calculating Sharpe Ratio: {}".format(e))
            return {'monthly': 'N/A', 'annual': 'N/A'}

    def __calculate_period_sharpe(self, closed_trades, risk_free_rate, period, start_date, end_date):
        """
        Calculate Sharpe Ratio for a specific period (monthly or annual).

        Args:
            closed_trades: List of closed trade dicts
            risk_free_rate: Annual risk-free rate as decimal
            period: 'monthly' or 'annual'
            start_date: datetime object
            end_date: datetime object

        Returns:
            Sharpe Ratio as float rounded to 2 decimals, or 'N/A' if can't calculate
        """
        try:
            # Group trades by period
            period_returns = {}

            for trade in closed_trades:
                # Parse trade close time
                try:
                    trade_time = datetime.strptime(trade['Time'], '%Y.%m.%d %H:%M')
                except:
                    logging.warning("Could not parse trade time: {}".format(trade['Time']))
                    continue

                # Determine period key
                if period == 'monthly':
                    period_key = trade_time.strftime('%Y-%m')
                else:  # annual
                    period_key = trade_time.strftime('%Y')

                # Aggregate returns for this period
                if period_key not in period_returns:
                    period_returns[period_key] = 0.0

                try:
                    period_returns[period_key] += float(trade['Return %'])
                except ValueError:
                    pass

            # Generate all periods in date range (including zero-return periods)
            all_periods = self.__generate_all_periods(start_date, end_date, period)

            # Create complete returns list with zeros for missing periods
            returns_list = []
            for period_key in all_periods:
                returns_list.append(period_returns.get(period_key, 0.0))

            # Need at least 2 periods to calculate standard deviation
            if len(returns_list) < 2:
                logging.warning("Insufficient periods for Sharpe calculation (need >= 2)")
                return 'N/A'

            # Calculate mean and std dev of returns
            mean_return = sum(returns_list) / len(returns_list)
            variance = sum((r - mean_return) ** 2 for r in returns_list) / (len(returns_list) - 1)
            std_return = math.sqrt(variance)

            # Avoid division by zero
            if std_return == 0:
                logging.warning("Zero standard deviation, Sharpe cannot be calculated")
                return 'N/A'

            # Adjust risk-free rate to period
            if period == 'monthly':
                period_rf = (risk_free_rate / 12.0) * 100  # Convert to monthly percentage
                periods_per_year = 12
            else:  # annual
                period_rf = risk_free_rate * 100  # Convert to annual percentage
                periods_per_year = 1

            # Calculate Sharpe Ratio
            # Sharpe = (Mean Return - Risk Free Rate) / Std Dev * sqrt(periods per year)
            sharpe = ((mean_return - period_rf) / std_return) * math.sqrt(periods_per_year)

            return round(sharpe, 2)

        except Exception as e:
            logging.error("Error in period Sharpe calculation: {}".format(e))
            return 'N/A'

    def __generate_all_periods(self, start_date, end_date, period):
        """
        Generate list of all period keys between start and end dates.

        Args:
            start_date: datetime object
            end_date: datetime object
            period: 'monthly' or 'annual'

        Returns:
            List of period keys as strings (e.g., ['2021-01', '2021-02', ...])
        """
        periods = []
        current = start_date

        if period == 'monthly':
            while current <= end_date:
                periods.append(current.strftime('%Y-%m'))
                current += relativedelta(months=1)
        else:  # annual
            while current <= end_date:
                periods.append(current.strftime('%Y'))
                current += relativedelta(years=1)

        return periods

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