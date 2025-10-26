//+------------------------------------------------------------------+
//Copyright © 2005, MetaQuotes Software Corp.
//Upgrade by Vlad
// v. 1.0
//+------------------------------------------------------------------+
#property  copyright "Copyright © 2005, MetaQuotes Software Corp. & Vlad 2010"
#property  link      "http://www.becemal.ru/mql/"
#property  indicator_separate_window
#property  indicator_buffers 2
#property  indicator_color1  LimeGreen
#property  indicator_color2  FireBrick
#property   indicator_width1  1
#property   indicator_width2  1
extern int RVIPeriod = 10;
//---- indicator buffers
double     RVIBuffer[];
double     RVISignalBuffer[];
int init()
  {
   SetIndexBuffer(0,RVIBuffer);
   SetIndexBuffer(1,RVISignalBuffer);
   SetIndexStyle(0,DRAW_LINE);
   SetIndexStyle(1,DRAW_LINE);
   SetIndexDrawBegin(0,RVIPeriod+3);   
   SetIndexDrawBegin(1,RVIPeriod+7);     
   IndicatorShortName("KosherRVI("+RVIPeriod+")");
   SetIndexLabel(0,"RVI");
   SetIndexLabel(1,"RVIS");
   return(0);
  }
int start()
  {
   int i, j, k, l, nLimit,nCountedBars = IndicatorCounted();
   double dValueUp,dValueDown,dNum,dDeNum, Norm;
   if((Bars <= (RVIPeriod + 8)) || (nCountedBars < 0)) return(0);
   nLimit = Bars - RVIPeriod - 4;
   if(nCountedBars > (RVIPeriod + 4)) nLimit = Bars - nCountedBars;
   for(i=0; i <= nLimit; i++)
     {
      dNum=0.0; 
      dDeNum=0.0;
      for(k = 0; k < RVIPeriod; k++)
        {
         j = k + i;
         Norm = RVIPeriod - k + 1;
         dNum += Norm * ((Volume[j]*(Close[j] - Open[j])+8*Volume[j+1]*(Close[j+1]-Open[j+1])+8*Volume[j+2]*(Close[j+2]-Open[j+2])+Volume[j+3]*(Close[j+3]-Open[j+3])));
         dDeNum += Norm * ((Volume[j]*(High[j]-Low[j])+8*Volume[j+1]*(High[j+1]-Low[j+1])+8*Volume[j+2]*(High[j+2]-Low[j+2])+Volume[j+3]*(High[j+3]-Low[j+3])));
         }
      if(dDeNum!=0.0)   RVIBuffer[i] = dNum/dDeNum;
      else  RVIBuffer[i] = dNum;   
     }
   nLimit = Bars - RVIPeriod - 7;
   if(nCountedBars > (RVIPeriod+8)) nLimit = Bars - nCountedBars + 1;
   for(i=0; i<=nLimit; i++)   RVISignalBuffer[i] = (4*RVIBuffer[i] + 3*RVIBuffer[i+1] + 2*RVIBuffer[i+2] + RVIBuffer[i+3])/10;
   return(0);
  }