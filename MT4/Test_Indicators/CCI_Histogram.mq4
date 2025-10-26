//+-------------------------------------------------------------------+
//|	Trailing_CCI_Trend.mq4
//| Based on Symphonie_Trendline_Indicator
//| !!! this file is created with Tab size 4 and no space indentation
//+-------------------------------------------------------------------+
#property copyright "Comer"
#property link		""

#property indicator_separate_window

#property indicator_buffers	2

#property indicator_color1	DodgerBlue
#property indicator_style1	STYLE_SOLID
#property indicator_width1	4

#property indicator_color2	Red
#property indicator_style2	STYLE_SOLID
#property indicator_width2	4


extern int CCI_Period = 45;

double CCI_Trigger_Level = 0.0;

double TrendUp[];
double TrendDown[];

int BarNumber;
int BarIndex;

int init() {
	SetIndexStyle ( 0, DRAW_HISTOGRAM );
	SetIndexBuffer( 0, TrendUp );
	
	SetIndexStyle ( 1, DRAW_HISTOGRAM );
	SetIndexBuffer( 1, TrendDown );
	
	return(0);
}
 
int deinit() {
	return(0);
}

int start() {
	BarNumber = IndicatorCounted();	// [0 .. Bars]
   
	for( BarIndex = Bars - BarNumber; BarIndex > 0; ) {
		BarIndex--;		// [Bars-1 .. 0]
		processBar();
		BarNumber++;
	}
   
	return(0);
}

void processBar() {
	double	cciNow;
	double	cciPrevious;
	bool	trendUp;

	if( BarNumber == 0 ) // BarIndex == Bars-1
		return;

	cciNow		= iCCI( NULL, 0, CCI_Period, PRICE_TYPICAL, BarIndex	);
	cciPrevious	= iCCI( NULL, 0, CCI_Period, PRICE_TYPICAL, BarIndex+1	);
	
	if( (cciNow > CCI_Trigger_Level) && (cciPrevious <= CCI_Trigger_Level) ) // crossed up through the trigger level
		trendUp = true;
	else
	if( (cciNow < CCI_Trigger_Level) && (cciPrevious >= CCI_Trigger_Level) ) // crossed down through the trigger level
		trendUp = false;
	else	// trend did not change
		trendUp = (TrendUp[BarIndex+1] != 0);

	if( trendUp ) {
		TrendUp[BarIndex] = 1;
		TrendDown[BarIndex] = 0;
	}
	else {
		TrendDown[BarIndex] = 1;
		TrendUp[BarIndex] = 0;
	}
}

