import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import CycleSelector from "../components/CycleSelector";
import DirectionSelector from "../components/DirectionSelector";
import { useDate } from "../contexts/DateContext";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, ScatterChart, Scatter, Area, AreaChart
} from "recharts";
import { RefreshCw, AlertCircle, CheckCircle2, TrendingUp, PieChart as PieChartIcon, BarChart3, Activity, Upload, Check, Scale } from "lucide-react";
import { Button } from "../components/ui/button";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "../components/ui/carousel";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/api";
import { generateDemoSummary, generateDemoHistorical } from "../lib/demoData";

// Historical data will be fetched from API

// Use distinct colors for charts - Bank/Compliance appropriate palette
const CHART_COLORS = {
  matched: "#10b981",      // Green for matched transactions
  unmatched: "#ef4444",    // Red for unmatched/errors
  brandBlue: "#3b82f6",    // Primary blue
  brandSky: "#0ea5e9",     // Sky blue for contrast
  allTxns: "#6366f1",      // Indigo for total transactions
  reconciled: "#22c55e",   // Bright green for reconciled
  purple: "#a855f7",       // Purple for variety
  amber: "#f59e0b",        // Amber for warnings
};

export default function Dashboard() {
  const { dateFrom, dateTo } = useDate();
  const [txnType, setTxnType] = useState("all");
  const [txnCategory, setTxnCategory] = useState("all");
  const [selectedCycle, setSelectedCycle] = useState("all");
  const [selectedDirection, setSelectedDirection] = useState("all");
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // DEMO MODE: Use demo data directly without backend calls
  const [summaryData] = useState(generateDemoSummary());
  const [historicalData] = useState(generateDemoHistorical());
  const isSummaryLoading = false;
  const isHistoricalLoading = false;
  const summaryError = null;

  const refreshData = () => {
    setLastRefresh(new Date());
    // Demo mode - no actual refresh needed
  };

  // Helper function to safely extract numeric values from summary data
  const getNumericValue = (data: any, keys: string[]): number => {
    for (const key of keys) {
      const value = key.split('.').reduce((obj, k) => obj?.[k], data);
      if (typeof value === 'number' && !isNaN(value)) return value;
    }
    return 0;
  };

  // Helper to extract from summary/breakdown structure
  const getFromSummaryOrBreakdown = (data: any, keys: string[]): number => {
    // Try from summary object first
    if (data?.summary) {
      for (const key of keys) {
        const value = key.split('.').reduce((obj, k) => obj?.[k], data.summary);
        if (typeof value === 'number' && !isNaN(value)) return value;
      }
    }
    // Try from breakdown object
    if (data?.breakdown) {
      for (const key of keys) {
        const value = key.split('.').reduce((obj, k) => obj?.[k], data.breakdown);
        if (typeof value === 'number' && !isNaN(value)) return value;
      }
    }
    // Fallback to top-level
    return getNumericValue(data, keys);
  };

  // Extract values with demo data fallback
  const matchedCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['matched.count', 'matched', 'reconciled']));
  const partialMatchesCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['partial_matches.count', 'partial_matches']));
  const hangingCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['hanging.count', 'hanging']));
  const unmatchedCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['unmatched.count', 'unmatched', 'breaks']));
  const exceptionsCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['exceptions.count', 'exceptions']));
  const totalCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['totals.count', 'total_transactions', 'total']));
  
  // Inflow/Outflow with absolute values
  const inwardCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['inflow_outflow.inward.count', 'inward.count']));
  const outwardCount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['inflow_outflow.outward.count', 'outward.count']));
  const inwardAmount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['inflow_outflow.inward.amount', 'inward.amount']));
  const outwardAmount = Math.abs(getFromSummaryOrBreakdown(summaryData, ['inflow_outflow.outward.amount', 'outward.amount']));
  
  // Dispute stats
  const disputeStats = summaryData?.disputes || {
    total: 0,
    open: 0,
    working: 0,
    closed: 0,
    byCategory: {},
    tatBreached: 0
  };

  const pieData = summaryData ? [
    { name: "Matched", value: matchedCount, color: CHART_COLORS.reconciled },
    { name: "Unmatched", value: unmatchedCount, color: CHART_COLORS.unmatched },
  ] : [];




  // DEMO MODE: Always show data immediately

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">UPI Reconciliation Overview</p>
          <p className="text-sm text-muted-foreground mt-1">
            Today's Reconciliation: {totalCount.toLocaleString()} transactions processed
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <Button variant="outline" size="sm" onClick={refreshData} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>




      {/* Error Display */}
      {summaryError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>Failed to load dashboard data. Please check backend connection.</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="recon" className="w-full">
        <TabsList className="bg-muted/30">
          <TabsTrigger value="recon" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Recon Dashboard
          </TabsTrigger>
          <TabsTrigger value="breaks" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Today's Recon
          </TabsTrigger>
          <TabsTrigger value="datewise" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Date-wise Details
          </TabsTrigger>
        </TabsList>

        {/* Recon Dashboard Tab */}
        <TabsContent value="recon" className="space-y-6 mt-6">
          {/* Recon Status Banner */}
          {summaryData && summaryData.run_id && (
            <Card className="shadow-lg bg-gradient-to-r from-blue-50 to-card border-blue-200">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-lg">Current Reconciliation Status</h3>
                    <p className="text-sm text-muted-foreground">Run ID: {summaryData.run_id}</p>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <span>Status:</span>
                      {summaryData.status === 'completed' ? (
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle2 className="h-4 w-4" />
                          Completed
                        </span>
                      ) : (
                        <span>{summaryData.status}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-green-600">{matchedCount}</div>
                    <div className="text-sm text-muted-foreground">Transactions Matched</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chart Carousel */}
          <Card className="shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Analytics Overview</CardTitle>
                  <p className="text-sm text-muted-foreground">Multiple chart views of reconciliation data</p>
                </div>
                <Select defaultValue="transaction">
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="transaction">Transaction Analysis</SelectItem>
                    <SelectItem value="monthly">Monthly Trend</SelectItem>
                    <SelectItem value="comparison">Comparison View</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent className="px-6 pb-6">
              <div className="w-full mx-auto px-4 py-2">
                <Carousel opts={{ align: "start" }} className="w-full">
                  <CarouselContent className="-ml-2 md:-ml-4">
                    {/* Pie Chart */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Transaction Distribution</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <PieChart>
                            <Pie
                              data={pieData.length > 0 ? pieData : [{ name: "No Data", value: 1, color: "#ccc" }]}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={85}
                              paddingAngle={2}
                              dataKey="value"
                              label={pieData.length > 0 ? ({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%` : undefined}
                            >
                              {(pieData.length > 0 ? pieData : [{ name: "No Data", value: 1, color: "#ccc" }]).map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => value.toLocaleString()} />
                            {pieData.length > 0 && <Legend verticalAlign="bottom" height={20} />}
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Bar Chart */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Monthly Comparison</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <BarChart data={historicalData && historicalData.length > 0 ? historicalData : []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              dataKey="month"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <YAxis
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <Tooltip
                              formatter={(value) => value.toLocaleString()}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                              }}
                            />
                            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                            <Bar dataKey="allTxns" fill={CHART_COLORS.allTxns} name="All Txns" radius={[6, 6, 0, 0]} />
                            <Bar dataKey="reconciled" fill={CHART_COLORS.reconciled} name="Reconciled" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Line Chart (Trend) */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Reconciliation Trend</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <LineChart data={historicalData && historicalData.length > 0 ? historicalData : []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              dataKey="month"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <YAxis
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <Tooltip
                              formatter={(value) => value.toLocaleString()}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                              }}
                            />
                            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                            <Line
                              type="monotone"
                              dataKey="allTxns"
                              stroke={CHART_COLORS.allTxns}
                              strokeWidth={3}
                              name="All Txns"
                              dot={{ fill: CHART_COLORS.allTxns, r: 4 }}
                              activeDot={{ r: 6 }}
                            />
                            <Line
                              type="monotone"
                              dataKey="reconciled"
                              stroke={CHART_COLORS.reconciled}
                              strokeWidth={3}
                              name="Reconciled"
                              dot={{ fill: CHART_COLORS.reconciled, r: 4 }}
                              activeDot={{ r: 6 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Success Rate Chart */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Success Rate Trend</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <BarChart data={historicalData && historicalData.length > 0 ? historicalData.map(d => ({
                            ...d,
                            successRate: d.allTxns > 0 ? Math.round((d.reconciled / d.allTxns) * 100) : 0
                          })) : []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              dataKey="month"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <YAxis
                              domain={[0, 100]}
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <Tooltip
                              formatter={(value) => `${value}%`}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                              }}
                            />
                            <Bar dataKey="successRate" fill={CHART_COLORS.reconciled} name="Success Rate %" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Scatter Diagram */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Transaction Scatter Analysis</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <ScatterChart data={historicalData && historicalData.length > 0 ? historicalData.map((d, index) => ({
                            x: index + 1,
                            y: d.allTxns,
                            z: d.reconciled,
                            month: d.month
                          })) : []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <XAxis
                              type="number"
                              dataKey="x"
                              name="Month"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <YAxis
                              type="number"
                              dataKey="y"
                              name="All Transactions"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <Tooltip
                              cursor={{ strokeDasharray: '3 3' }}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                              }}
                              formatter={(value, name) => [value.toLocaleString(), name]}
                              labelFormatter={(label) => `Month ${label}`}
                            />
                            <Scatter
                              name="All Transactions"
                              dataKey="y"
                              fill={CHART_COLORS.allTxns}
                            />
                          </ScatterChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Stock-like Line Chart (Area Chart) */}
                    <CarouselItem className="pl-2 md:pl-4 md:basis-full">
                      <div className="p-4">
                        <h3 className="text-center font-semibold mb-2 text-foreground text-sm">Reconciliation Performance</h3>
                        <ResponsiveContainer width="100%" height={280}>
                          <AreaChart data={historicalData && historicalData.length > 0 ? historicalData.map(d => ({
                            ...d,
                            successRate: d.allTxns > 0 ? Math.round((d.reconciled / d.allTxns) * 100) : 0,
                            unmatchedRate: d.allTxns > 0 ? Math.round((d.allTxns - d.reconciled) / d.allTxns * 100) : 0
                          })) : []}>
                            <defs>
                              <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={CHART_COLORS.reconciled} stopOpacity={0.8} />
                                <stop offset="95%" stopColor={CHART_COLORS.reconciled} stopOpacity={0.1} />
                              </linearGradient>
                              <linearGradient id="colorUnmatched" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={CHART_COLORS.unmatched} stopOpacity={0.8} />
                                <stop offset="95%" stopColor={CHART_COLORS.unmatched} stopOpacity={0.1} />
                              </linearGradient>
                            </defs>
                            <XAxis
                              dataKey="month"
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <YAxis
                              domain={[0, 100]}
                              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                              stroke="hsl(var(--border))"
                            />
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                            <Tooltip
                              formatter={(value) => `${value}%`}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                              }}
                            />
                            <Area
                              type="monotone"
                              dataKey="successRate"
                              stackId="1"
                              stroke={CHART_COLORS.reconciled}
                              fillOpacity={1}
                              fill="url(#colorSuccess)"
                              name="Success Rate %"
                            />
                            <Area
                              type="monotone"
                              dataKey="unmatchedRate"
                              stackId="1"
                              stroke={CHART_COLORS.unmatched}
                              fillOpacity={1}
                              fill="url(#colorUnmatched)"
                              name="Unmatched Rate %"
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>
                  </CarouselContent>
                  <div className="flex items-center justify-center gap-4 mt-4">
                    <CarouselPrevious className="static translate-y-0 hover:bg-brand-blue hover:text-white transition-colors" />
                    <div className="text-center text-xs text-muted-foreground px-4">
                      Swipe or use arrows to view different charts
                    </div>
                    <CarouselNext className="static translate-y-0 hover:bg-brand-blue hover:text-white transition-colors" />
                  </div>
                </Carousel>
              </div>
            </CardContent>
          </Card>

          {/* Dispute Overview Card */}
          {disputeStats.total > 0 && (
            <Card className="shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Dispute Management Overview</CardTitle>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => window.location.href = '/disputes'}
                  >
                    View All Disputes
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Scale className="w-4 h-4 text-muted-foreground" />
                      <span className="text-xs font-medium text-muted-foreground">Total</span>
                    </div>
                    <div className="text-xl font-bold">{disputeStats.total}</div>
                  </div>
                  <div className="text-center p-3 bg-orange-50 rounded-lg">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-orange-600" />
                      <span className="text-xs font-medium text-orange-700">Open</span>
                    </div>
                    <div className="text-xl font-bold text-orange-600">{disputeStats.open}</div>
                  </div>
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-blue-600" />
                      <span className="text-xs font-medium text-blue-700">Working</span>
                    </div>
                    <div className="text-xl font-bold text-blue-600">{disputeStats.working}</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      <span className="text-xs font-medium text-green-700">Closed</span>
                    </div>
                    <div className="text-xl font-bold text-green-600">{disputeStats.closed}</div>
                  </div>
                </div>
                
                {disputeStats.tatBreached > 0 && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600" />
                      <span className="text-sm font-medium text-red-700">
                        {disputeStats.tatBreached} dispute{disputeStats.tatBreached > 1 ? 's' : ''} with TAT breach
                      </span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* KPI Cards - Reconciliation Metrics */}
          <div className="grid grid-cols-4 gap-6">
            <Card className="bg-gradient-to-br from-brand-light to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Txns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-brand-blue">
                      {totalCount.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Processed</div>
                  </div>
                  <BarChart3 className="h-10 w-10 text-brand-blue opacity-20" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-green-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Matched</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-green-600">
                      {matchedCount.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {((matchedCount/totalCount)*100).toFixed(1)}% Rate
                    </div>
                  </div>
                  <CheckCircle2 className="h-10 w-10 text-green-600 opacity-20" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-orange-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Unmatched</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-orange-600">
                      {unmatchedCount.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Need Review</div>
                  </div>
                  <AlertCircle className="h-10 w-10 text-orange-600 opacity-20" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-yellow-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Hanging</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-yellow-600">
                      {hangingCount.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Pending</div>
                  </div>
                  <Activity className="h-10 w-10 text-yellow-600 opacity-20" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Inflow/Outflow Breakdown with Trend Comparison */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Inflow / Outflow Analysis</CardTitle>
              <p className="text-sm text-muted-foreground">Transaction direction analysis and trend comparison</p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-green-700">Inward (Credit)</h4>
                    <TrendingUp className="w-4 h-4 text-green-600" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Count:</span>
                      <span className="font-semibold">{inwardCount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Amount:</span>
                      <span className="font-semibold">₹{(inwardAmount/10000000).toFixed(2)}Cr</span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-red-700">Outward (Debit)</h4>
                    <Activity className="w-4 h-4 text-red-600" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Count:</span>
                      <span className="font-semibold">{outwardCount.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Amount:</span>
                      <span className="font-semibold">₹{(outwardAmount/10000000).toFixed(2)}Cr</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Trend Comparison Chart */}
              <div className="border-t pt-6">
                <h4 className="text-sm font-semibold mb-4">Inward vs Outward Trend Comparison</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={historicalData && historicalData.length > 0 ? historicalData : []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      stroke="hsl(var(--border))"
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      stroke="hsl(var(--border))"
                    />
                    <Tooltip
                      formatter={(value) => value.toLocaleString()}
                      contentStyle={{
                        backgroundColor: "hsl(var(--background))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                    <Line
                      type="monotone"
                      dataKey="inward"
                      stroke="#10b981"
                      strokeWidth={2}
                      name="Inward"
                      dot={{ fill: "#10b981", r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="outward"
                      stroke="#ef4444"
                      strokeWidth={2}
                      name="Outward"
                      dot={{ fill: "#ef4444", r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Validation Summary */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Validation Summary</CardTitle>
              <p className="text-sm text-muted-foreground">Transaction validation results and error analysis</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Overall Stats */}
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="text-lg font-bold text-green-600">
                    {summaryData?.validation?.passed?.toLocaleString() || '0'}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Passed</div>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="text-lg font-bold text-red-600">
                    {summaryData?.validation?.failed?.toLocaleString() || '0'}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Failed</div>
                </div>
                <div className="text-center p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="text-lg font-bold text-yellow-600">
                    {summaryData?.validation?.warnings?.toLocaleString() || '0'}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Warnings</div>
                </div>
                <div className="text-center p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="text-lg font-bold text-orange-600">
                    {summaryData?.validation?.criticalErrors?.toLocaleString() || '0'}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Critical</div>
                </div>
              </div>

              {/* Validation by Type */}
              <div className="border-t pt-4">
                <h4 className="text-sm font-semibold mb-3">Validation by Type</h4>
                <div className="space-y-2">
                  {Object.entries(summaryData?.validation?.byType || {}).map(([type, count]) => {
                    const total = summaryData?.validation?.totalValidated || 1;
                    const percentage = ((count as number / total) * 100).toFixed(1);
                    return (
                      <div key={type} className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">{type}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-green-500" 
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-12 text-right">{percentage}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Today's Breaks Tab */}
        <TabsContent value="breaks" className="space-y-6 mt-6">
          <Card className="shadow-lg bg-gradient-to-r from-yellow-50 to-card border-yellow-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">Today's Reconciliation Breaks</h3>
                  <p className="text-sm text-muted-foreground">
                    Transactions from today's reconciliation that require attention
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-yellow-600">
                    {unmatchedCount}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Breaks to resolve
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {summaryData && unmatchedCount > 0 ? (
            <>
              {/* Break Analysis Cards */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="shadow-lg">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Total Breaks</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-yellow-600">
                          {unmatchedCount}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Requiring action</p>
                      </div>
                      <AlertCircle className="h-8 w-8 text-yellow-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="shadow-lg bg-gradient-to-br from-orange-50 to-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Partial Matches</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-orange-600">
                          {Math.floor(unmatchedCount * 0.6)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Can be force matched</p>
                      </div>
                      <Activity className="h-8 w-8 text-orange-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="shadow-lg bg-gradient-to-br from-red-50 to-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Hanging Transactions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-red-600">
                          {hangingCount}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">{totalCount > 0 ? ((hangingCount / totalCount) * 100).toFixed(1) : 0}% of total</p>
                      </div>
                      <AlertCircle className="h-8 w-8 text-red-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="shadow-lg bg-gradient-to-br from-blue-50 to-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-blue-600">
                          {totalCount > 0 ? Math.round((matchedCount / totalCount) * 100) : 0}%
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Reconciliation rate</p>
                      </div>
                      <TrendingUp className="h-8 w-8 text-blue-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Break Distribution Chart */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle>Break Distribution</CardTitle>
                  <p className="text-sm text-muted-foreground">Today's breakup by category</p>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Partial Matches", value: partialMatchesCount, color: "hsl(270, 95%, 75%)" },
                          { name: "Hanging Transactions", value: hangingCount, color: "hsl(0, 84%, 60%)" },
                          { name: "True Unmatched", value: unmatchedCount, color: "hsl(39, 100%, 50%)" }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={3}
                        dataKey="value"
                        label={(entry) => `${entry.name} ${((entry.value / (partialMatchesCount + hangingCount + unmatchedCount)) * 100).toFixed(1)}%`}
                        labelLine={{ stroke: '#666', strokeWidth: 1 }}
                      >
                        <Cell fill="hsl(270, 95%, 75%)" />
                        <Cell fill="hsl(0, 84%, 60%)" />
                        <Cell fill="hsl(39, 100%, 50%)" />
                      </Pie>
                      <Tooltip
                        formatter={(value) => value.toLocaleString()}
                        contentStyle={{
                          backgroundColor: "hsl(var(--background))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                        }}
                      />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Action Buttons */}
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle>Next Steps</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    className="w-full rounded-full bg-brand-blue hover:bg-brand-mid"
                    onClick={() => window.location.href = '/unmatched'}
                  >
                    View Unmatched Transactions
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full rounded-full"
                    onClick={() => window.location.href = '/force-match'}
                  >
                    Use Force Matching Tool
                  </Button>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="shadow-lg">
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <CheckCircle2 className="w-16 h-16 mx-auto text-green-500 mb-4" />
                  <p className="text-lg font-semibold text-green-600">Perfect Reconciliation!</p>
                  <p className="text-muted-foreground mt-2">
                    All transactions have been successfully reconciled with zero breaks.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Date-wise Details Tab */}
        <TabsContent value="datewise" className="space-y-6 mt-6">
          <Card className="shadow-lg bg-gradient-to-r from-indigo-50 to-card border-indigo-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">Date-wise Reconciliation Details</h3>
                  <p className="text-sm text-muted-foreground">
                    Detailed breakdown of reconciliation activities by date
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-indigo-600">
                    {historicalData ? historicalData.length : 0}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Days with data
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Date-wise Summary Table */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Reconciliation Summary by Date</CardTitle>
              <p className="text-sm text-muted-foreground">Historical reconciliation performance across dates</p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-3 font-medium text-muted-foreground">Date</th>
                      <th className="text-right p-3 font-medium text-muted-foreground">Total Txns</th>
                      <th className="text-right p-3 font-medium text-muted-foreground">Matched</th>
                      <th className="text-right p-3 font-medium text-muted-foreground">Unmatched</th>
                      <th className="text-right p-3 font-medium text-muted-foreground">Success Rate</th>
                      <th className="text-right p-3 font-medium text-muted-foreground">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historicalData && historicalData.length > 0 ? (
                      historicalData.map((item, index) => {
                        const successRate = item.allTxns > 0 ? Math.round((item.reconciled / item.allTxns) * 100) : 0;
                        return (
                          <tr key={index} className="border-b border-border hover:bg-muted/50">
                            <td className="p-3 font-medium">{item.month}</td>
                            <td className="p-3 text-right">{item.allTxns.toLocaleString()}</td>
                            <td className="p-3 text-right text-green-600">{item.reconciled.toLocaleString()}</td>
                            <td className="p-3 text-right text-red-600">{(item.allTxns - item.reconciled).toLocaleString()}</td>
                            <td className="p-3 text-right">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${successRate >= 90 ? 'bg-green-100 text-green-800' :
                                  successRate >= 70 ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-red-100 text-red-800'
                                }`}>
                                {successRate}%
                              </span>
                            </td>
                            <td className="p-3 text-right font-medium">
                              ₹{((item.allTxns || 0) * 150).toLocaleString()}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-muted-foreground">
                          No historical data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Date-wise Trend Chart */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Date-wise Performance Trend</CardTitle>
              <p className="text-sm text-muted-foreground">Visual representation of reconciliation performance over time</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={historicalData && historicalData.length > 0 ? historicalData.map(d => ({
                  ...d,
                  successRate: d.allTxns > 0 ? Math.round((d.reconciled / d.allTxns) * 100) : 0,
                  date: d.month
                })) : []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    stroke="hsl(var(--border))"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    stroke="hsl(var(--border))"
                  />
                  <Tooltip
                    formatter={(value) => `${value}%`}
                    contentStyle={{
                      backgroundColor: "hsl(var(--background))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                            <Line
                              type="monotone"
                              dataKey="successRate"
                              stroke={CHART_COLORS.reconciled}
                              strokeWidth={3}
                              name="Success Rate %"
                              dot={{ fill: CHART_COLORS.reconciled, r: 4 }}
                              activeDot={{ r: 6 }}
                            />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Date Range Filter for Details */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Filter Date Range</CardTitle>
              <p className="text-sm text-muted-foreground">Select specific date range to view detailed reconciliation data</p>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium">Current Date Range</label>
                  <div className="flex gap-2">
                    <input
                      type="date"
                      value={dateFrom}
                      readOnly
                      className="flex-1 px-3 py-2 border rounded-lg bg-muted"
                    />
                    <span className="self-center">To</span>
                    <input
                      type="date"
                      value={dateTo}
                      readOnly
                      className="flex-1 px-3 py-2 border rounded-lg bg-muted"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">Date range is controlled globally from the top bar</p>
                </div>
                <Button
                  onClick={refreshData}
                  className="bg-primary hover:bg-secondary"
                >
                  Refresh Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
