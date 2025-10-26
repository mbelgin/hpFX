//+------------------------------------------------------------------+
// Internal revision: v6 (cosmetic) — converted single-literal debug Alerts to Dbg(...)
//|                                                  hpFX_Engine.mq4 |
//|                                     Copyright 2025 Mehmet Belgin |
//|                                 https://github.com/mbelgin/hpFX  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025 Mehmet Belgin"
#property link      "https://github.com/mbelgin/hpFX"
#property version   "1.011"
#property strict
//=============================================================================
// hpFX_Engine — configuration quick reference
//-----------------------------------------------------------------------------
// Indicator definition schema (indi_defs_#):
//   "<name> | <type> | <params>"
//
// Indicator types and params:
//   BASELINECROSS  : <indi_inputs>;<indi_filename>;<buffer or buffer1,buffer2>
//   TWOLINESCROSS  : <indi_inputs>;<indi_filename>;<buffer1,buffer2>
//   ONELEVELCROSS  : <indi_inputs>;<indi_filename>;<buffer>;<level>
//   TWOLEVELCROSS  : <indi_inputs>;<indi_filename>;<(+/-)buffer>;<high_level,low_level>
//   SLOPE          : <indi_inputs>;<indi_filename>;<buffer>
//   HISTOGRAM      : <indi_inputs>;<indi_filename>;<long_buffer,short_buffer>
//   LINEMACROSS    : <indi_inputs>;<indi_filename>;<buffer>;<MA_period,MA_type[0..3]>
//   ARROWS         : <indi_inputs>;<indi_filename>;<long_buffer,short_buffer>
//   SINGLEBUFFER   : <indi_inputs>;<indi_filename>;<buffer>
//
// Usage (indi_usage_#):
//   SIGNAL, SIGNALEXIT, CONFIRMATION, TRADEORNOT, STOPLOSS, EXIT, DISABLED
//
// Notes:
//   - Buffers are 1-based in config; code converts to 0-based (MT4 default)internally.
//   - Negative buffer index means logical inversion where supported (e.g., TWOLEVELCROSS, BASELINECROSS).
//   - TRADEORNOT acts as a veto: LONG means "allowed to trade" in this context, otherwise NOTRADE.
//   - DAILY timeframe logic is used for ATR, candles, and many indicator reads (PERIOD_D1).
//   - debug_output=true enables additional [DEBUG] messages.
//
// Examples:
//   "QQEA_SAME_AS_QQEx50 | ONELEVELCROSS | ;Test_Indicators\\QQEA;1;50"
//   "QQEAdvXMA_12_SMA    | LINEMACROSS   | ;Test_Indicators\\QQE Adv;1;12,0"
//   "LSMA_COLOR          | SLOPE         | ;Test_Indicators\\LSMA_Color;1"
//   "SILVERTREND_SIGNAL  | ARROWS        | ;Test_Indicators\\SilverTrend_Signal;1,2"
//=============================================================================


enum t_trade
  {
   LONG,
   SHORT,
   NOTRADE,
   PASS
  };

enum t_indi
  {
   NONE,
   BASELINECROSS, // <indi_parameters>;<indi_filename>;<buffer1>
   TWOLINESCROSS, // <indi_parameters>;<indi_filename>;<buffer1>,<buffer2>
   ONELEVELCROSS, // <indi_parameters>;<indi_filename>;<buffer>;<level>
   TWOLEVELCROSS, // <indi_parameters>;<indi_filename>;<(+/-)buffer>;<high_level>,<low_level>
   SLOPE,         // <indi_parameters>;<indi_filename>;<buffer>
   HISTOGRAM,     // <indi_parameters>;<indi_filename>;<buffer1>,<buffer2>
   LINEMACROSS,   // <indi_parameters>;<indi_filename>;<buffer1>;<MA_period>,<MA_type>
   ARROWS,        // <indi_parameters>;<indi_filename>;<long_buffer>,<short_buffer>
   SINGLEBUFFER   // <indi_parameters>;<indi_filename>;<buffer>
  };

enum t_indi_usage
  {
   SIGNAL,
   SIGNALEXIT,
   CONFIRMATION,
   TRADEORNOT,
   STOPLOSS,
   EXIT,
   DISABLED
  };

enum t_candle
  {
   UNKNOWN,
   BULLISH,
   BEARISH,
   DOJI
  };

#define NUMINDIS 10

string indi_defs[NUMINDIS];
t_indi_usage indi_usage[NUMINDIS];
bool indi_based_trsl = false;
string trailing_sl_indi="";
int sl_be_tickets[];
int cycle_counter = 0;
float current_lot = 0.0;

extern string indi_defs_1 = "";                 // Indicator #1 definition
extern t_indi_usage indi_usage_1 = DISABLED;    // Indicator #1 usage
extern string indi_defs_2 = "";                 // Indicator #2 definition
extern t_indi_usage indi_usage_2 = DISABLED;    // Indicator #2 usage
extern string indi_defs_3 = "";                 // Indicator #3 definition
extern t_indi_usage indi_usage_3 = DISABLED;    // Indicator #3 usage
extern string indi_defs_4 = "";                 // Indicator #4 definition
extern t_indi_usage indi_usage_4 = DISABLED;    // Indicator #4 usage
extern string indi_defs_5 = "";                 // Indicator #5 definition
extern t_indi_usage indi_usage_5 = DISABLED;    // Indicator #5 usage
extern string indi_defs_6 = "";                 // Indicator #6 definition
extern t_indi_usage indi_usage_6 = DISABLED;    // Indicator #6 usage
extern string indi_defs_7 = "";                 // Indicator #7 definition
extern t_indi_usage indi_usage_7 = DISABLED;    // Indicator #7 usage
extern string indi_defs_8 = "";                 // Indicator #8 definition
extern t_indi_usage indi_usage_8 = DISABLED;    // Indicator #8 usage
extern string indi_defs_9 = "";                 // Indicator #9 definition
extern t_indi_usage indi_usage_9 = DISABLED;    // Indicator #9 usage
extern string indi_defs_10 = "";                // Indicator #10 definition
extern t_indi_usage indi_usage_10 = DISABLED;   // Indicator #10 usage

extern string  div2 = "----------------------"; // ---- TRADING CONDITIONS -----
extern int     min_before_candle_close = 5;     // Trading window before candle close (min)
extern double  max_spread_pips = 10.0;          // Max spread to take trades
extern int     max_slippage_points = 100;       // Max allowed slippage in points

extern string  div3 = "----------------------"; // ----- RISK MANAGEMENT ------
extern double  risk_percent = 2;                // Risk per trade (percent)
extern double  opt_first_order_risk = 100.0;    // 1st order risk % (use 100.0 for single trade)
extern double  opt_1st_sl_atr_multiplier = 1.5; // 1st SL ATR multiplier
extern double  opt_1st_tp_atr_multiplier = 3.0; // 1st TP ATR multiplier (0 to leave it open)
extern double  opt_2nd_sl_atr_multiplier = 1.5; // 2nd SL ATR multiplier
extern double  opt_2nd_tp_atr_multiplier = 3.0; // 2nd TP ATR multiplier (0 to leave it open)
extern bool    no_indiexit_on_first_trade = false;  // Do NOT check exit conditions on the first trade
extern bool    add_spread_to_tp = false;        // Add current spread to TP
extern bool    require_matching_candle = false; // Require matching candle to trade
extern double  sl_to_be_R = 0.0;                // R to move SL->BE

extern string  div4 = "----------------------"; // --------- VARIOUS ----------
extern bool    debug_output = false;            // Debug output (enables banner/debug logs)
extern bool    repaint_check = false;           // (BETA) Perform a repaint check and exit instead of running tests
extern double  doji_percent = 10.0;             // Percent of daily range for a candle to be considered 'doji'

extern string  div5 = "----------------------"; // ------- ROULETTE MM --------
extern bool    roulette_money_mng = false;      // (BETA) Enable Roulette Money Management
extern int     cycle_target = 4;                // (BETA) Consecutive wins cycle target
extern double  lot_multiplier_percent = 100.0;  // (BETA) Percent of calculated risk to use as increments
extern double  profit_loss_threshold = 50.0;    // (BETA) Min P/L amount (+/-) to consider an order (to filter out fees)


//+------------------------------------------------------------------+
//| Utilities (cosmetic only)                                        |
//+------------------------------------------------------------------+
void Dbg(string msg)
  {
   if(debug_output)
      Print("[DEBUG]", msg);
  }

void Err(string msg, int ticket=0)
  {
   if(ticket != 0)
      Print("[ERROR] ", msg, " (ticket #", ticket, ")");
   else
      Print("[ERROR] ", msg);
   Print("TERMINATING EA.");
   ExpertRemove();
  }


//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
  if (Period() != PERIOD_D1)
     {
      Err("hpFX_Engine must be attached to the DAILY (D1) timeframe.");
      return(-1);
     }

// Basic input validation
   if((opt_1st_sl_atr_multiplier == 0.0) || (opt_2nd_sl_atr_multiplier == 0.0))
     {
      Err("Initial SL multipliers cannot be zero.");
     }

  if((roulette_money_mng == true) && (opt_first_order_risk != 100.0))
     {
      Err("Roulette MM and partial trades are mutually exclusive (opt_first_order_risk must be 100.0).");
     }

// Mirror externs into arrays (kept as-is for compatibility)
   indi_defs[0] = indi_defs_1;
   indi_usage[0] = indi_usage_1;
   indi_defs[1] = indi_defs_2;
   indi_usage[1] = indi_usage_2;
   indi_defs[2] = indi_defs_3;
   indi_usage[2] = indi_usage_3;
   indi_defs[3] = indi_defs_4;
   indi_usage[3] = indi_usage_4;
   indi_defs[4] = indi_defs_5;
   indi_usage[4] = indi_usage_5;
   indi_defs[5] = indi_defs_6;
   indi_usage[5] = indi_usage_6;
   indi_defs[6] = indi_defs_7;
   indi_usage[6] = indi_usage_7;
   indi_defs[7] = indi_defs_8;
   indi_usage[7] = indi_usage_8;
   indi_defs[8] = indi_defs_9;
   indi_usage[8] = indi_usage_9;
   indi_defs[9] = indi_defs_10;
   indi_usage[9] = indi_usage_10;

   for(int i=0; i < NUMINDIS; i++)
     {
      if((indi_usage[i] == STOPLOSS) && (indi_defs[i] != ""))
        {
         indi_based_trsl = true;
         trailing_sl_indi = indi_defs[i];
        }
     }

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
// Reserved for cleanup
  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {

   static bool tokenClaimed = false;

   int symbol_tickets[];

   bool trading_window = isWithinTradeHours();

   if(!trading_window)
     {
      // Keep token unclaimed when outside of the trading window
      tokenClaimed = false;
      return;
     }

   if(tokenClaimed == true)
     {
      return;
     }
   else
     {
      tokenClaimed = true;
      if(debug_output)
         Print("[DEBUG] Trading window is open.");

      // Pre-evaluate signals before checking active trades (to refresh zones)
      t_trade indi_says[NUMINDIS];
      t_trade exit_indi_says[NUMINDIS];
      ArrayInitialize(indi_says, NOTRADE);
      ArrayInitialize(exit_indi_says, NOTRADE);

      if((indi_usage[0] != SIGNAL) && (indi_usage[0]!=SIGNALEXIT))
        {
         Err("First indicator must be SIGNAL or SIGNALEXIT.");
        }

      int num_signal_indis = 0;
      int num_stoploss_indis = 0;
      for(int i=0; i < NUMINDIS; i++)
        {
         if(indi_defs[i] == "" || indi_usage[i] == EXIT || indi_usage[i] == STOPLOSS || indi_usage[i] == DISABLED)
           {
            indi_says[i] = PASS;
            continue;
           }

         // TRADEORNOT evaluated as a confirmation-style condition
         if(indi_usage[i] == TRADEORNOT)
           {
            if(debug_output)
               Dbg("Evaluating TRADEORNOT: ");
            indi_says[i] = eval_trade(indi_defs[i], CONFIRMATION);
           }
         else
           {
            indi_says[i] = eval_trade(indi_defs[i], indi_usage[i]);
           }

         // Track presence of SIGNAL/SIGNALEXIT and STOPLOSS
         if((indi_usage[i] == SIGNAL) || (indi_usage[i] == SIGNALEXIT))
            ++num_signal_indis;

         if(indi_usage[i] == STOPLOSS)
            ++num_stoploss_indis;
        }

      if(num_signal_indis == 0)
        {
         Err("At least one SIGNAL or SIGNALEXIT indicator must be defined.");
        }

      if(num_stoploss_indis > 1)
        {
         Err("Only one STOPLOSS indicator can be defined.");
        }

      listCurrentOrders(symbol_tickets);

      // Handle open orders, if any
      if(ArraySize(symbol_tickets) == 2)
        {
         // Check orders with no SL
         checkOrdersWithNoSL(symbol_tickets);
         if(!no_indiexit_on_first_trade)
           {
            handleExitConditions(symbol_tickets, exit_indi_says);
           }
        }

      if(ArraySize(symbol_tickets) == 1)
        {
         if(indi_based_trsl)
           {
            handleTrailingSL(symbol_tickets[0], trailing_sl_indi);
           }
         if(sl_to_be_R > 0.0)
           {
            move_sl_to_be(symbol_tickets[0]);
           }
         handleExitConditions(symbol_tickets, exit_indi_says);
        }

      if(ArraySize(symbol_tickets) > 2)
        {
         Err("Found 2+ open orders; closing all and terminating EA.");
         terminateAllOrders(symbol_tickets);
         Err("EA terminated after closing all orders.");
        }

      // Completed processing open tickets; bail if any remain
      int refreshed_symbol_tickets[];
      listCurrentOrders(refreshed_symbol_tickets);
      if(ArraySize(refreshed_symbol_tickets) > 0)
         return;

      double cur_spread = MarketInfo(Symbol(), MODE_SPREAD)/10.0;

      // Check Spread
      if(cur_spread > max_spread_pips)
        {
         Print("INFO: Current spread (", cur_spread, ") exceeds max (", max_spread_pips, "). Skipping trade.");
         return;
        }

      // Build agreement across indicators (TRADEORNOT is a veto unless LONG)
      t_trade agreement = PASS;

      for(int i=0; i < NUMINDIS; i++)
        {
         if(indi_says[i] == PASS)
            continue;

         if(agreement == PASS)
            agreement = indi_says[i];

         if(indi_usage[i] == TRADEORNOT)
           {
            if(indi_says[i] == LONG)
              {
               // LONG means "allowed to trade"
               continue;
              }
            else
              {
               agreement = NOTRADE;
               break;
              }
           }
         // Any disagreement means no trade
         if(indi_says[i] != agreement)
           {
            agreement = NOTRADE;
            break;
           }
        }

      t_candle candle_type = candleType();

      if(require_matching_candle && (candle_type != DOJI))
        {
         if((agreement==LONG && candle_type==BEARISH) || (agreement==SHORT && candle_type==BULLISH))
           {
            Print("INFO: Trade aborted due to candle mismatch.");
            agreement = NOTRADE;
           }
        }

      sendOrder(agreement);

     }
  }

//+------------------------------------------------------------------+
//| List current orders for this symbol                              |
//+------------------------------------------------------------------+
void listCurrentOrders(int &symbol_tickets[])
  {
   int total_open_orders = OrdersTotal();

   for(int order=0; order<total_open_orders; order++)
     {
      if(OrderSelect(order, SELECT_BY_POS) == false)
         continue;
      if(OrderSymbol() == Symbol())
        {
         ArrayResize(symbol_tickets, ArraySize(symbol_tickets) + 1);
         symbol_tickets[ArraySize(symbol_tickets) - 1] = OrderTicket();
        }
     }

   for(int i=0; i < ArraySize(symbol_tickets); i++)
     {
      Print("[INFO] Active trade #", i+1, " ticket=", symbol_tickets[i], " type=", OrderType());
     }
   return;
  }

//+------------------------------------------------------------------+
//| Current spread expressed as price delta                          |
//+------------------------------------------------------------------+
double getSpreadPrice()
  {
   double spread = MarketInfo(Symbol(), MODE_SPREAD); // points
   return spread * Point;
  }

//+------------------------------------------------------------------+
//| Trading window: last N minutes of the current day                |
//+------------------------------------------------------------------+
bool isWithinTradeHours()
  {
   int time_in_candle = int(TimeCurrent()-Time[0]);
   int sec_in_day = 24 * 60 * 60;
   int trade_window_start = sec_in_day - (min_before_candle_close * 60);

   if((time_in_candle > trade_window_start))
     {
      return true;
     }
   else
     {
      return false;
     }
  }

//+------------------------------------------------------------------+
//| Trailing SL driven by a SINGLEBUFFER custom indicator            |
//+------------------------------------------------------------------+
void handleTrailingSL(int ticket, string input_line)
  {

   string s_entry[];
   string indi_config[];

   int num_fields = parse_input(input_line, '|', s_entry);

   if(num_fields != 3)
     {
      Print("ERROR(handleTrailingSL): expected 3 '|' fields, found ", num_fields, ".");
     }


   string c_name = string(s_entry[0]);
   string c_type = string(s_entry[1]);
   string c_pars = string(s_entry[2]);


   if(c_type != "SINGLEBUFFER")
     {
      Print("ERROR: ", "STOPLOSS indicators support only SINGLEBUFFER type.");
      Print("TERMINATING EA.");
      ExpertRemove();
     }

   string indi_pars[3];
   int num_indis = parse_input(c_pars, ';', indi_pars);

   string indi_inputs      = string(indi_pars[0]);
   string indi_file        = string(indi_pars[1]);
   string indi_buffers_str = string(indi_pars[2]);
   string indi_buffers[1];

   int num_indi_buffers = parse_input(indi_buffers_str, ',', indi_buffers);
   if(num_indi_buffers != 1)
     {
      Print("ERROR: ", "SINGLEBUFFER STOPLOSS requires exactly one buffer.");
      Print("TERMINATING EA.");
      ExpertRemove();
     }

   int indi_buffer = int(indi_buffers_str) - 1;
   double stoploss_indi_val = iCustom(Symbol(), PERIOD_D1, indi_file, indi_buffer, 0);

   if(OrderSelect(ticket, SELECT_BY_TICKET))
     {
      if(((OrderType() == OP_BUY) && (stoploss_indi_val > Bid)) || ((OrderType() == OP_SELL) && (stoploss_indi_val < Ask)))
        {
         Print("WARNING: STOPLOSS indicator value is on the wrong side; not modifying SL.");
         return;
        }

      if(OrderModify(OrderTicket(), OrderOpenPrice(), stoploss_indi_val, OrderTakeProfit(), Yellow))
        {
         Print("INFO: Modified SL to STOPLOSS indicator (", stoploss_indi_val, ") for ticket ", ticket, ".");
        }
      else
        {
         Print("ERROR: ", "Cannot modify SL to STOPLOSS indicator for ticket ", ticket, ".");
         Print("TERMINATING EA.");
         ExpertRemove();
         //;
         return;
        }
     }
   else
     {
      Print("ERROR: Cannot select ticket for SL->STOPLOSS (ticket ", ticket, ").");
      return;
     }
  }

//+------------------------------------------------------------------+
//| Move SL to BE after reaching sl_to_be_R * 1R                     |
//+------------------------------------------------------------------+
void move_sl_to_be(int ticket)
  {
   if(OrderSelect(ticket, SELECT_BY_TICKET))
     {
      // Check if SL is already moved to BE for this ticket
      for(int i=0; i<ArraySize(sl_be_tickets); i++)
        {
         if(ticket == sl_be_tickets[i])
           {
            Print("INFO: SL already moved to BE; no action.");
            return;
           }
        }
     }
   else
     {
      Err("SL->BE: Cannot select order (ticket " + string (ticket) + ").");
     }

   double sl_be_trigger  = OrderOpenPrice() + ((OrderOpenPrice() - OrderStopLoss()) * sl_to_be_R);

   if(((OrderType() == 0)&&(Ask>sl_be_trigger))||((OrderType()==1)&&(Bid<sl_be_trigger)))
     {
      Print("INFO: Moving SL->BE (open=", OrderOpenPrice(), ").");
      bool result = OrderModify(OrderTicket(), OrderOpenPrice(), OrderOpenPrice(), OrderTakeProfit(), 0, Yellow);
      if(!result)
        {
         Print("ERROR(SL->BE): Failed moving SL->BE for order ", ticket, ".");
         Print("ERROR DETAILS: ", GetLastError());
         Print("ERROR CONTEXT: ticket=", ticket, " type=", OrderType(), " sl_be_trigger=", sl_be_trigger, " entry=", OrderOpenPrice(), " SL=", OrderStopLoss(), " TP=", OrderTakeProfit());
         Print("TERMINATING EA.");
         ExpertRemove();
        }
      Print("INFO: Successfully moved SL->BE.");
      ArrayResize(sl_be_tickets, ArraySize(sl_be_tickets) + 1);
      sl_be_tickets[ArraySize(sl_be_tickets) - 1] = ticket;
     }
  }

//+------------------------------------------------------------------+
//| Ensure all open orders have SL; close offenders                  |
//+------------------------------------------------------------------+
void checkOrdersWithNoSL(int &symbol_tickets[])
  {
   for(int i=0; i<ArraySize(symbol_tickets); i++)
     {
      int cur_ticket = symbol_tickets[i];
      if(OrderSelect(cur_ticket, SELECT_BY_TICKET))
        {
         double cur_sl = OrderStopLoss();
         if(cur_sl == 0.0)
           {
            Print("ALERT: Ticket ", cur_ticket, " has no SL; closing.");
            closeOrder(cur_ticket);
           }
        }
      else
        {
         Print("ERROR: ", "Selecting order ", cur_ticket, " failed (code ", GetLastError(), ").");
         Print("TERMINATING EA.");
         ExpertRemove();
        }
     }
  }


//+------------------------------------------------------------------+
//| Close a single order                                             |
//+------------------------------------------------------------------+
bool closeOrder(int ticket)
  {
   if(!OrderSelect(ticket, SELECT_BY_TICKET))
     {
      Print("ERROR: Selecting ticket for closing failed (ticket ", ticket, ").");
      return false;
     }
   else
     {
      Print("INFO: Closing ticket ", ticket, ".");

      double lots_cur_ticket = OrderLots();

      if(OrderClose(ticket, lots_cur_ticket, Bid, max_slippage_points, Yellow))
        {
         Print("INFO: Closed ticket ", ticket, " successfully.");
         return true;
        }
      else
        {
         Print("ERROR: Failed closing ticket ", ticket, ".");
         return false;
        }
     }
  }


//+------------------------------------------------------------------+
//| Terminate all orders in list                                     |
//+------------------------------------------------------------------+
void terminateAllOrders(int &symbol_tickets[])
  {

   for(int i=0; i<ArraySize(symbol_tickets); i++)
     {
      int cur_ticket =  symbol_tickets[i];
      if(OrderSelect(symbol_tickets[i], SELECT_BY_TICKET))
        {
         if(closeOrder(cur_ticket))
           {
            Print("INFO: Terminated ticket ", cur_ticket, ".");
           }
         else
           {
            Print("ERROR: Failed terminating ticket ", cur_ticket, ".");
           }
        }
      else
        {
         Print("ERROR: Selecting order ", cur_ticket, " failed.");
        }
     }
  }

//+------------------------------------------------------------------+
//| Convert String to enum for the switch case block                 |
//+------------------------------------------------------------------+
template<typename T>
T StringToEnum(string str,T enu)
  {
   for(int i=0; i<256; i++)
      if(EnumToString(enu=(T)i)==str)
         return(enu);
//---
   return(-1);
  }

//+------------------------------------------------------------------+
//| Split string into fields and trim                                |
//+------------------------------------------------------------------+
int parse_input(string inp_line, const ushort separator, string &results[])
  {
// Parses given input, adds fields in results[], and returns the number of fields found.
   int num_fields = StringSplit(inp_line, separator, results);

   for(int i=0; i < num_fields; i++)
      results[i] = StringTrimRight(StringTrimLeft(results[i]));

   return num_fields;
  }

//+------------------------------------------------------------------+
//| Evaluate indicator and return trade directive                    |
//+------------------------------------------------------------------+
t_trade eval_trade(string input_line, t_indi_usage usage)
  {

   string s_entry[];
   string indi_config[];
   static t_trade arrow_zone = NOTRADE;
   static t_trade hist_zone = NOTRADE;

   int num_fields = parse_input(input_line, '|', s_entry);

   if(num_fields != 3)
     {
      Print("ERROR(eval_trade): expected 3 '|' fields, found ", num_fields, ".");
     }

   string c_name = string(s_entry[0]);
   string c_type = string(s_entry[1]);
   string c_pars = string(s_entry[2]);

   t_indi selection = NONE;
   int expression = StringToEnum(c_type, selection);

   switch(expression)
     {
      case ONELEVELCROSS: //<indi_parameters>;<indi_filename>;<buffer>;<level>
        {
         Dbg("ONELEVELCROSS");
         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 4)
           {
            Print("ERROR: ", "ONELEVELCROSS expects 4 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs   = string(indi_pars[0]);
         string indi_file     = string(indi_pars[1]);
         int indi_buffer      = int(indi_pars[2]) - 1;
         double indi_level    = double(indi_pars[3]);

         double indi_buffer_now    = iCustom(Symbol(), 0, indi_file, indi_buffer, 0);
         double indi_buffer_pre    = iCustom(Symbol(), 0, indi_file, indi_buffer, 1);

         if(debug_output)
            Dbg("verify now:");

         if(indi_buffer_now > indi_level) //LONG
           {
            if(usage == CONFIRMATION)
              {
               Dbg("CONFIRMATION LONG");
               return LONG;
              }
            if(indi_buffer_pre <= indi_level)
              {
               Dbg("LONG");
               return  LONG;
              }
           }
         else
            if(indi_buffer_now < indi_level) //SHORT
              {
               if(usage == CONFIRMATION)
                 {
                  return SHORT;
                 }

               if(indi_buffer_pre >= indi_level)
                 {
                  Dbg("SHORT");
                  return SHORT;
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;
      case TWOLINESCROSS:
        {
         if(debug_output)
            Dbg("TWOLINESCROSS"); // <indi_parameters>;<indi_filename>;<buffer1>,<buffer2>));
         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 3)
           {
            Print("ERROR: ", "TWOLINESCROSS expects 3 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         string indi_buffers_str = string(indi_pars[2]);
         string indi_buffers[2];

         int num_indi_buffers = parse_input(indi_buffers_str, ',', indi_buffers);
         if(num_indi_buffers != 2)
           {
            Print("ERROR: ", "TWOLINESCROSS expects 2 buffers, found ", num_indi_buffers, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         int indi_buffer_1 = int(indi_buffers[0]) - 1;
         int indi_buffer_2 = int(indi_buffers[1]) - 1;

         double indi_buffer_1_now    = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 0);
         double indi_buffer_1_pre    = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 1);
         double indi_buffer_2_now    = iCustom(Symbol(), 0, indi_file, indi_buffer_2, 0);
         double indi_buffer_2_pre    = iCustom(Symbol(), 0, indi_file, indi_buffer_2, 1);

         if(indi_buffer_1_now > indi_buffer_2_now) //LONG
           {
            if(usage == CONFIRMATION)
              {
               return LONG;
              }
            if(indi_buffer_1_pre <= indi_buffer_2_pre)
              {
               Dbg("LONG");
               return LONG;
              }
           }
         else
            if(indi_buffer_1_now < indi_buffer_2_now) //SHORT
              {
               if(usage == CONFIRMATION)
                 {
                  return SHORT;
                 }
               if(indi_buffer_1_pre >= indi_buffer_2_pre)
                 {
                  Dbg("SHORT");
                  return SHORT;
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }

      break;
      case SLOPE:
        {
         if(debug_output)
            Dbg("SLOPE"); // <indi_parameters>;<indi_filename>;<buffer1> (1-index)));
         string indi_pars[];
         bool reverse = false;
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 3)
           {
            Print("ERROR: ", "SLOPE expects 3 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         string indi_buffers_str = string(indi_pars[2]);
         string indi_buffers[1];

         int num_indi_buffers = parse_input(indi_buffers_str, ',', indi_buffers);
         if(num_indi_buffers != 1)
           {
            Print("ERROR: ", "SLOPE expects exactly one buffer, found ", num_indi_buffers, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         int indi_buffer = int(indi_buffers[0]);
         if(indi_buffer < 0)
            reverse = true;
         indi_buffer = MathAbs(indi_buffer) - 1;

         double indi_buffer_now    = iCustom(Symbol(), 0, indi_file, indi_buffer, 0);
         double indi_buffer_pre1   = iCustom(Symbol(), 0, indi_file, indi_buffer, 1);
         double indi_buffer_pre2   = iCustom(Symbol(), 0, indi_file, indi_buffer, 2);

         if(indi_buffer_now > indi_buffer_pre1) // Upward slope
           {
            if(usage == CONFIRMATION)
              {
               return (reverse ? SHORT : LONG);
              }

            if(indi_buffer_pre1 <= indi_buffer_pre2)
              {
               if(debug_output)
                  Dbg("");
               return (reverse ? SHORT : LONG);
              }
           }
         else
            if(indi_buffer_now < indi_buffer_pre1) // Downward slope
              {
               if(usage == CONFIRMATION)
                 {
                  return (reverse ? LONG : SHORT);
                 }

               if(indi_buffer_pre1 >= indi_buffer_pre2)
                 {
                  if(debug_output)
                     Dbg("");
                  return (reverse ? LONG : SHORT);
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;

      case HISTOGRAM:
        {
         if(debug_output)
            Dbg("HISTOGRAM"); // <indi_parameters>;<indi_filename>;<buffer1>,<buffer2> (1-index)));

         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 3)
           {
            Print("ERROR: ", "HISTOGRAM expects 3 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         string indi_buffers_str = string(indi_pars[2]);
         string indi_buffers[2];

         int num_indi_buffers = parse_input(indi_buffers_str, ',', indi_buffers);

         if(num_indi_buffers != 2)
           {
            Print("ERROR: ", "HISTOGRAM expects 2 buffers, found ", num_indi_buffers, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         int indi_buffer_long = int(indi_buffers[0]) - 1;
         int indi_buffer_short = int(indi_buffers[1]) - 1;

         if(debug_output)
            Dbg("buffers: long=");

         double indi_buffer_long_now   = iCustom(Symbol(), 0, indi_file, indi_buffer_long, 0);
         double indi_buffer_long_pre   = iCustom(Symbol(), 0, indi_file, indi_buffer_long, 1);
         double indi_buffer_short_now  = iCustom(Symbol(), 0, indi_file, indi_buffer_short, 0);
         double indi_buffer_short_pre  = iCustom(Symbol(), 0, indi_file, indi_buffer_short, 1);

         double compare;
         if((indi_buffer_long_now == EMPTY_VALUE) || (indi_buffer_short_now == EMPTY_VALUE))
            compare = EMPTY_VALUE;
         else
            if((indi_buffer_long_now == 0.0) || (indi_buffer_short_now == 0.0))
               compare = 0.0;
            else   //INCONCLUSIVE
              {
               if(debug_output)
                  Print("HISTOGRAM inconclusive -> NOTRADE");
               return NOTRADE;
              }

         if(indi_buffer_long_now != compare)
           {
            if(hist_zone == NOTRADE)
               hist_zone = LONG;

            if(usage == CONFIRMATION)
              {
               return LONG;
              }

            if(hist_zone == SHORT)
              {
               Dbg("LONG");
               hist_zone = LONG;
               return LONG;
              }
           }
         else
            if(indi_buffer_short_now != compare) // SEE IF OVERLAPS NEED TO BE HANDLED (e.g. REVERSALNAVI)
              {
               if(hist_zone == NOTRADE)
                  hist_zone = SHORT;

               if(usage == CONFIRMATION)
                 {
                  return SHORT;
                 }
               if(hist_zone == LONG)
                 {
                  Dbg("SHORT");
                  hist_zone = SHORT;
                  return SHORT;
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;
      case LINEMACROSS:
        {
         if(debug_output)
            Dbg("LINEMACROSS"); // <indi_parameters>;<indi_filename>;<buffer1>;<MA_period>,<MA_type>));
         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 4)
           {
            Print("ERROR: ", "LINEMACROSS expects 4 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs   = string(indi_pars[0]);
         string indi_file     = string(indi_pars[1]);
         int indi_buffer      = int(indi_pars[2]) - 1;
         string indi_ma_str   = string(indi_pars[3]);
         string indi_ma[2];

         int num_indi_ma = parse_input(indi_ma_str, ',', indi_ma);
         if(num_indi_ma != 2)
           {
            Print("ERROR: ", "MA_period, MA_type expects 2 values, found ", num_indi_ma, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         int indi_ma_period = int(indi_ma[0]);
         int indi_ma_type   = int(indi_ma[1]);

         if(indi_ma_type > 3)
           {
            Print("ERROR: ", "MA_type must be [0-3] (0=SMA, 1=EMA, 2=SMMA, 3=LWMA)");
            Print("TERMINATING EA.");
            ExpertRemove();
            //.");
           }

         double indi_buffer_now    = iCustom(Symbol(), 0, indi_file, indi_buffer, 0);
         double indi_buffer_pre    = iCustom(Symbol(), 0, indi_file, indi_buffer, 1);

         const int buffer_size = indi_ma_period + 10; // safe margin
         double indi_ma_buffer[];
         ArrayResize(indi_ma_buffer, buffer_size);
         for(int i=0; i<buffer_size; i++)
           {
            indi_ma_buffer[i] = iCustom(Symbol(), 0, indi_file, indi_buffer, buffer_size-i);
           }

         double indi_ma_now  = iMAOnArray(indi_ma_buffer, 0, indi_ma_period, 0, indi_ma_type, 0);
         double indi_ma_pre  = iMAOnArray(indi_ma_buffer, 0, indi_ma_period, 0, indi_ma_type, 1);

         if(indi_buffer_now > indi_ma_now)
           {
            if(usage == CONFIRMATION)
              {
               return LONG;
              }
            if(indi_buffer_pre <= indi_ma_pre)
              {
               Dbg("LONG");
               return LONG;
              }
           }
         else
            if(indi_buffer_now < indi_ma_now)
              {
               if(usage == CONFIRMATION)
                 {
                  return SHORT;
                 }
               if(indi_buffer_pre >= indi_ma_pre)
                 {
                  Dbg("SHORT");
                  return SHORT;
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;
      case TWOLEVELCROSS:
        {
         Dbg("TWOLEVELCROSS");
         string indi_pars[];
         bool reverse = false;
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 4)
           {
            Print("ERROR: ", "TWOLEVELCROSS expects 4 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         int indi_buffer         = int(indi_pars[2]);

         if(indi_buffer < 0)
            reverse = true;

         indi_buffer = int(MathAbs(indi_buffer)) - 1;

         string indi_levels_str  = string(indi_pars[3]);
         string indi_levels[2];
         int num_indi_levels = parse_input(indi_levels_str, ',', indi_levels);
         if(num_indi_levels != 2)
           {
            Print("ERROR: ", "TWOLEVELCROSS expects 2 level values, found ", num_indi_levels, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         double level_sell = double(indi_levels[0]); // First level = SELL
         double level_buy  = double(indi_levels[1]); // Second level = BUY

         double indi_now = iCustom(Symbol(), 0, indi_file, indi_buffer, 0);
         double indi_pre = iCustom(Symbol(), 0, indi_file, indi_buffer, 1);

         if(usage == CONFIRMATION)
           {
            if(indi_now >= level_buy)
               return (reverse ? SHORT : LONG);
            if(indi_now <= level_sell)
               return (reverse ? LONG : SHORT);
            return NOTRADE;
           }

         if((indi_pre < level_buy) && (indi_now >= level_buy))
            return (reverse ? SHORT : LONG);

         if((indi_pre > level_sell) && (indi_now <= level_sell))
            return (reverse ? LONG : SHORT);

         return NOTRADE;
        }
      break;

      case BASELINECROSS:
        {
         if(debug_output)
            Dbg("BASELINECROSS"); // <indi_parameters>;<indi_filename>;<buffer>));
         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 3)
           {
            Print("ERROR: ", "BASELINECROSS expects 3 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         string indi_buffer_str  = string(indi_pars[2]);

         string indi_buffers[];
         int num_indi_buffers = parse_input(indi_buffer_str, ',', indi_buffers);

         double indi_buffer_now = EMPTY_VALUE;
         double indi_buffer_pre = EMPTY_VALUE;

         bool invert = false;

         if(num_indi_buffers == 2)
           {
            int raw_1 = int(indi_buffers[0]);
            int raw_2 = int(indi_buffers[1]);

            if(raw_1 < 0)
              {
               invert = !invert;
               raw_1 = -raw_1;
              }
            if(raw_2 < 0)
              {
               invert = !invert;
               raw_2 = -raw_2;
              }

            int indi_buffer_1 = raw_1 - 1;
            int indi_buffer_2 = raw_2 - 1;

            indi_buffer_now = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 0);
            if(indi_buffer_now == EMPTY_VALUE)
               indi_buffer_now = iCustom(Symbol(), 0, indi_file, indi_buffer_2, 0);

            if(indi_buffer_now == EMPTY_VALUE)
              {
               Print("ERROR: ", "Both buffers in BASELINECROSS returned EMPTY_VALUE (now).");
               Print("TERMINATING EA.");
               ExpertRemove();
               //.");
              }

            indi_buffer_pre = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 1);
            if(indi_buffer_pre == EMPTY_VALUE)
               indi_buffer_pre = iCustom(Symbol(), 0, indi_file, indi_buffer_2, 1);

            if(indi_buffer_pre == EMPTY_VALUE)
              {
               Print("ERROR: ", "Both buffers in BASELINECROSS returned EMPTY_VALUE (pre).");
               Print("TERMINATING EA.");
               ExpertRemove();
               //.");
              }
           }
         else
            if(num_indi_buffers == 1)
              {
               int raw_1 = int(indi_buffers[0]);
               if(raw_1 < 0)
                 {
                  invert = true;
                  raw_1 = -raw_1;
                 }
               int indi_buffer_1 = raw_1 - 1;

               indi_buffer_now = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 0);
               indi_buffer_pre = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 1);
              }
            else
              {
               Print("ERROR: ", "BASELINECROSS expects 1 or 2 buffer indices.");
               Print("TERMINATING EA.");
               ExpertRemove();
              }

         double ask_price_now = Ask;
         double close_pre = iClose(Symbol(), PERIOD_D1, 1);

         if((ask_price_now > indi_buffer_now && !invert) || (ask_price_now < indi_buffer_now && invert))
           {
            if(usage == CONFIRMATION)
              {
               return LONG;
              }

            if((close_pre <= indi_buffer_pre && !invert) || (close_pre >= indi_buffer_pre && invert))
              {
               Dbg("LONG");
               return LONG;
              }
           }
         else
            if((ask_price_now < indi_buffer_now && !invert) || (ask_price_now > indi_buffer_now && invert))
              {
               if(usage == CONFIRMATION)
                 {
                  return SHORT;
                 }

               if((close_pre >= indi_buffer_pre && !invert) || (close_pre <= indi_buffer_pre && invert))
                 {
                  Dbg("SHORT");
                  return SHORT;
                 }
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;
      case ARROWS:
        {
         if(debug_output)
            Dbg("ARROWS"); // <indi_parameters>;<indi_filename>;<long_buffer>,<short_buffer>));

         // Needed for confirmation
         int num_bars = iBars(Symbol(), PERIOD_D1);

         string indi_pars[];
         int num_indi_pars = parse_input(c_pars, ';', indi_pars);
         if(num_indi_pars != 3)
           {
            Print("ERROR: ", "ARROWS expects 3 parameters, found ", num_indi_pars, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }
         string indi_inputs      = string(indi_pars[0]);
         string indi_file        = string(indi_pars[1]);
         string indi_buffers_str = string(indi_pars[2]);
         string indi_buffers[2];

         int num_indi_buffers = parse_input(indi_buffers_str, ',', indi_buffers);
         if(num_indi_buffers != 2)
           {
            Print("ERROR: ", "ARROWS expects 2 buffers, found ", num_indi_buffers, ".");
            Print("TERMINATING EA.");
            ExpertRemove();
            //;
           }

         int indi_buffer_1 = int(indi_buffers[0]) - 1;
         int indi_buffer_2 = int(indi_buffers[1]) - 1;

         double indi_buffer_long    = iCustom(Symbol(), 0, indi_file, indi_buffer_1, 0);
         double indi_buffer_short   = iCustom(Symbol(), 0, indi_file, indi_buffer_2, 0);

         // For ARROWS, actively scan back for last arrow to maintain state during open trades
         if(usage == CONFIRMATION)
           {
            for(int i=0; i < num_bars; i++)
              {
               double arrow_long  = iCustom(Symbol(), 0, indi_file, indi_buffer_1, i);
               double arrow_short = iCustom(Symbol(), 0, indi_file, indi_buffer_2, i);

               bool is_arrow_long  = ((arrow_long != EMPTY_VALUE) && (arrow_long != 0.0));
               bool is_arrow_short = ((arrow_short != EMPTY_VALUE) && (arrow_short != 0.0));

               if(is_arrow_long && !is_arrow_short)
                  return LONG;
               else
                  if(is_arrow_short && !is_arrow_long)
                     return SHORT;
              }
           }

         if(((indi_buffer_long != EMPTY_VALUE) && (indi_buffer_short == EMPTY_VALUE)) || ((indi_buffer_long != 0.0) && (indi_buffer_short == 0.0)))
           {
            Dbg("LONG");
            return LONG;

           }
         else
            if(((indi_buffer_long == EMPTY_VALUE) && (indi_buffer_short != EMPTY_VALUE)) || ((indi_buffer_long == 0.0) && (indi_buffer_short != 0.0)))
              {
               Dbg("SHORT");
               return SHORT;
              }
            else
              {
               Dbg("NOTRADE");
               return NOTRADE;
              }
        }
      break;
      default:
        {
         Print("ERROR: ", "Unknown configuration type: ", c_type, ".");
         Print("TERMINATING EA.");
         ExpertRemove();
         //;
        }
      break;
     }

   return NOTRADE;

  }

//+------------------------------------------------------------------+
//| Lot size calculation                                             |
//+------------------------------------------------------------------+
double calculateLotSize(string symbol, double stop_loss_delta)
  {
   double min_lot_size = MarketInfo(symbol, MODE_MINLOT); // 0.01
   double max_lot_size = MarketInfo(symbol, MODE_MAXLOT); // 1000
   double balance = AccountBalance();
   double free_margin = AccountFreeMargin();
   double tick_value = MarketInfo(symbol, MODE_TICKVALUE);
   double tick_size = MarketInfo(symbol, MODE_TICKSIZE);
   double min_stop_level = MarketInfo(symbol, MODE_STOPLEVEL);
   static int profit_counter = 0;

   double stop_loss_pips = stop_loss_delta / Point / 10.;

   Print("INFO: StopLossPips=", stop_loss_pips, " TickValue=", tick_value, " TickSize=", tick_size, " MinStopLevel=", min_stop_level);

   if((Digits == 3) || (Digits == 5))
      tick_value = tick_value * 10.;

   double base_lot_size = (balance * risk_percent/100.) / ((stop_loss_pips) * tick_value);
   double lot_size = base_lot_size;

   if(roulette_money_mng)
     {
      Print("INFO: ----- Roulette MM evaluation start -----");
      int total_orders = OrdersHistoryTotal();
      double profit = -9999;

      // Check the last qualifying order only
      if(total_orders > 0)
        {
         for(int i = (total_orders - 1); i > 0; i--)
           {
            if(OrderSelect(i, SELECT_BY_POS, MODE_HISTORY) == false)
              {
               Print("ERROR: ", "Cannot read history in calculateLotSize(), order index = ", i, ".");
               Print("TERMINATING EA.");
               ExpertRemove();
               //, order index = ", i);
               Print("TERMINATING EA.");
               ExpertRemove();
              }

            profit  = OrderProfit();
            int ticket     = OrderTicket();
            if(MathAbs(profit) >= MathAbs(profit_loss_threshold))
              {
               Print("INFO: Last qualifying ticket: ", ticket," with |P/L| >= ", profit_loss_threshold);
               break;
              }
           }

         if(profit < 0.0)
           {
            Print("INFO: Last qualifying trade was a loss; base lot size remains.");
            lot_size = base_lot_size;
            profit_counter = 0;
           }

         if(profit >= 0.0)
           {
            ++profit_counter;
            if(profit_counter == cycle_target)
              {
               Print("INFO: Cycle target reached; resetting base lot size.");
               lot_size = base_lot_size;
               profit_counter = 0;
              }
            Print("INFO: Increasing lot size; profit_counter=", profit_counter);
            lot_size = base_lot_size * (profit_counter + 1) * (lot_multiplier_percent / 100.0);
           }
        }
      else
        {
         Print("INFO: No historical orders yet.");
        }

      Print("INFO: ----- Roulette MM evaluation end -----");
     }
   Print("INFO: Balance=", balance, " FreeMargin=", free_margin);
   Print("INFO: BaseLotSize=", base_lot_size, " CurrentLotSize=", lot_size);

   return lot_size;

  }

//+------------------------------------------------------------------+
//| Send order(s) using current agreement                            |
//+------------------------------------------------------------------+
bool sendOrder(t_trade type)
  {
   if((type == PASS) || (type == NOTRADE))
      return true;

// Calculate SL/TP and lot sizes based on ATR (daily)
   double cur_atr    = iATR(Symbol(), PERIOD_D1, 14, 0); // price delta
   double cur_spread  = 0.0;
   if(add_spread_to_tp)
      cur_spread = getSpreadPrice();
   double stop_loss_delta_1   = (cur_atr * opt_1st_sl_atr_multiplier);
   double stop_loss_delta_2   = (cur_atr * opt_2nd_sl_atr_multiplier);
   double take_profit_delta_1 = (cur_atr * opt_1st_tp_atr_multiplier) + cur_spread;
   double take_profit_delta_2 = (cur_atr * opt_2nd_tp_atr_multiplier) + cur_spread;
   double lot_size_1 = calculateLotSize(Symbol(), stop_loss_delta_1) * (opt_first_order_risk/100.0);
   double lot_size_2 = 0.0;
   if(opt_first_order_risk != 100.0)
     {
      lot_size_2 = calculateLotSize(Symbol(), stop_loss_delta_2) * (100.0 - opt_first_order_risk)/100.0;
     }
   double min_lot_size = MarketInfo(Symbol(), MODE_MINLOT);
   int lot_digits = int (MathLog10(1./min_lot_size));

// Proper rounding of Lot size based on broker configuration.
   double norm_lot_size_1 = NormalizeDouble(lot_size_1, lot_digits);
   double norm_lot_size_2 = NormalizeDouble(lot_size_2, lot_digits);

   if(type == LONG)
     {
      double tp1 = Bid + take_profit_delta_1;
      double sl1 = Bid - stop_loss_delta_1;
      double tp2 = Bid + take_profit_delta_2;
      double sl2 = Bid - stop_loss_delta_2;

      if(opt_1st_tp_atr_multiplier == 0.0)
        {
         Print("INFO: First TP set to 0.");
         tp1 = 0.0;
        }
      if(opt_2nd_tp_atr_multiplier == 0.0)
        {
         Print("INFO: Second TP set to 0.");
         tp2 = 0.0;
        }

      int ticket = -1;
      // Open first half with TP
      Print("ORDER: BUY #1 lots=", lot_size_1, " SL=", sl1, " TP=", tp1);
      ticket = OrderSend(Symbol(), OP_BUY, norm_lot_size_1, Ask, max_slippage_points, sl1, tp1, "First buy order with TP");
      if(ticket < 0)
        {
         Print("ERROR: Sending buy #1 failed (", GetLastError(), ") lots=", norm_lot_size_1);
         return false;
        }
      else
        {
         Print("INFO: BUY #1 sent. Ticket=", ticket);
        }

      // Open second half only if risk is specified for the second order
      if(100.0 - opt_first_order_risk > 0)
        {
         ticket = -1;
         Print("ORDER: BUY #2 lots=", lot_size_2, " SL=", sl2, " TP=", tp2);
         ticket = OrderSend(Symbol(), OP_BUY, norm_lot_size_2, Ask, max_slippage_points, sl2, tp2, "Second buy order without TP");
         if(ticket < 0)
           {
            Print("ERROR: Sending buy #2 failed (", GetLastError(), ") lots=", norm_lot_size_2);
            return false;
           }
         else
           {
            Print("INFO: BUY #2 sent. Ticket=", ticket);
           }
        }
     }
   else
      if(type == SHORT)
        {
         double tp1 = Ask - take_profit_delta_1;
         double sl1 = Ask + stop_loss_delta_1;
         double tp2 = Ask - take_profit_delta_2;
         double sl2 = Ask + stop_loss_delta_2;

         if(opt_1st_tp_atr_multiplier == 0.0)
           {
            Print("INFO: First TP set to 0.");
            tp1 = 0.0;
           }
         if(opt_2nd_tp_atr_multiplier == 0.0)
           {
            Print("INFO: Second TP set to 0.");
            tp2 = 0.0;
           }

         int ticket = -1;

         // Open first half with TP
         Print("ORDER: SELL #1 lots=", lot_size_1, " SL=", sl1, " TP=", tp1);
         ticket = OrderSend(Symbol(), OP_SELL, norm_lot_size_1, Bid, max_slippage_points, sl1, tp1, "First sell order with TP");
         if(ticket < 0)
           {
            Print("ERROR: Sending sell #1 failed (", GetLastError(), ") lots=", norm_lot_size_1);
            return false;
           }
         else
           {
            Print("INFO: SELL #1 sent. Ticket=", ticket);
           }

         // Open second half only if risk is specified for the second order
         if(100.0 - opt_first_order_risk > 0)
           {
            Print("ORDER: SELL #2 lots=", lot_size_2, " SL=", sl2, " TP=", tp2);
            ticket = -1;
            ticket = OrderSend(Symbol(), OP_SELL, norm_lot_size_2, Bid, max_slippage_points, sl2, tp2, "Second sell order with no TP");

            if(ticket < 0)
              {
               Print("ERROR: Sending sell #2 failed (", GetLastError(), ") lots=", norm_lot_size_2);
               return false;
              }
            else
              {
               Print("INFO: SELL #2 sent. Ticket=", ticket);
              }
           }
        }
      else
        {
         Print("ERROR: Unknown order type: ", type);
         return false;
        }
   return true;

  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Repaint check (stub)                                             |
//+------------------------------------------------------------------+
bool checkRepaint(string indicator, int &buffers[])
  {

// TBD
   bool rp_detected = false;

   Dbg("Repainting check (stub)");

   static double buffers_array[][10];

   int num_buffers=ArraySize(buffers);

   if(num_buffers > 10)
     {
      Print("ERROR: Repaint check supports up to 10 buffers; requested ", num_buffers, ".");
     }

   for(int b=0; b < num_buffers; b++)
     {
      double cur_buffer = iCustom(Symbol(), 0, indicator, buffers[b] - 1, 0);
      ArrayResize(buffers_array, ArraySize(buffers_array) + 1);
      buffers_array[ArraySize(buffers_array)-1][b] = cur_buffer;
     }

   return rp_detected;
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Apply exit rules for SIGNALEXIT/EXIT indicators                  |
//+------------------------------------------------------------------+
void handleExitConditions(int &symbol_tickets[], t_trade &exit_indi_says[])
  {

   for(int i=0; i<NUMINDIS; i++)
     {
      if((indi_usage[i] == SIGNALEXIT) || (indi_usage[i] == EXIT))
         exit_indi_says[i] = eval_trade(indi_defs[i], SIGNAL);
     }

   for(int t=0; t<ArraySize(symbol_tickets); t++)
     {
      int ticket_order_type = -1;

      if(!OrderSelect(symbol_tickets[t], SELECT_BY_TICKET))
        {
         Print("ERROR: ", "Failed selecting order ", t, " to check exit conditions.");
         Print("TERMINATING EA.");
         ExpertRemove();
         //;
        }
      else
        {
         ticket_order_type = OrderType();
        }

      for(int i=0; i<NUMINDIS; i++)
        {
         if((exit_indi_says[i] == LONG && ticket_order_type == OP_SELL) ||
            (exit_indi_says[i] == SHORT && ticket_order_type == OP_BUY))
           {
            closeOrder(symbol_tickets[t]);
           }
        }
     }
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Candle classification                                            |
//+------------------------------------------------------------------+
t_candle candleType()
  {
   t_candle tmp_candle_type = UNKNOWN;

   double day_open      = iOpen(NULL, PERIOD_D1, 0);
   double day_high      = iHigh(NULL, PERIOD_D1, 0);
   double day_low       = iLow(NULL, PERIOD_D1, 0);
   double current_price = Ask;
   double range         = day_high - day_low;
   double day_close     = iClose(NULL, PERIOD_D1, 0);
   double body_height   = MathAbs(day_open - day_close);

   if(current_price >= day_open)
     {
      tmp_candle_type = BULLISH;
     }
   else
     {
      tmp_candle_type = BEARISH;
     }

   double body_percent = (body_height * 100.) / range;

// Mark doji if body is small relative to range
   if(body_percent <= doji_percent)
      tmp_candle_type = DOJI;

   return tmp_candle_type;
  }
//+------------------------------------------------------------------+
