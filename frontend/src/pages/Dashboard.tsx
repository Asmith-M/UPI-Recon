import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import CycleSelector from "../components/CycleSelector";
import DirectionSelector from "../components/DirectionSelector";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, ScatterChart, Scatter, Area, AreaChart
} from "recharts";
import { RefreshCw, AlertCircle, CheckCircle2, TrendingUp, PieChart as PieChartIcon, BarChart3, Activity } from "lucide-react";
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

// Historical data will be fetched from API

// Use theme colors for charts
const CHART_COLORS = {
  matched: "hsl(142, 76%, 36%)",
  unmatched: "hsl(0, 84%, 60%)",
  brandBlue: "hsl(var(--brand-blue))",
  brandSky: "hsl(var(--brand-sky))",
};

export default function Dashboard() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [txnType, setTxnType] = useState("all");
  const [txnCategory, setTxnCategory] = useState("all");
  const [selectedCycle, setSelectedCycle] = useState("all");
  const [selectedDirection, setSelectedDirection] = useState("all");
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Fetch summary data from API
  const { data: summaryData, isLoading: isSummaryLoading, error: summaryError, refetch: refetchSummary } = useQuery({
    queryKey: ['summary'],
    queryFn: apiClient.getSummary,
    retry: 1,
  });

  // Fetch historical data for charts
  const { data: historicalData, isLoading: isHistoricalLoading } = useQuery({
    queryKey: ['historical'],
    queryFn: apiClient.getHistoricalSummary,
    retry: 1,
  });

  const refreshData = () => {
    setLastRefresh(new Date());
    refetchSummary();
  };

  // Prepare pie chart data from summary
  const pieData = summaryData ? [
    { name: "Matched", value: (summaryData.matched?.count ?? summaryData.matched ?? 0), color: CHART_COLORS.matched },
    { name: "Unmatched", value: (summaryData.unmatched?.count ?? summaryData.unmatched ?? 0), color: CHART_COLORS.unmatched },
  ] : [];

  // Prepare summary display data
  const summaryDisplayData = summaryData ? [
    { label: "Total Transactions", amount: (summaryData.totals?.count ?? summaryData.total_transactions ?? 0).toLocaleString(), count: "" },
    { label: "Matched", amount: (summaryData.matched?.amount ?? 0).toLocaleString(), count: summaryData.matched?.count ? summaryData.matched.count.toLocaleString() : "" },
    { label: "Unmatched", amount: (summaryData.unmatched?.amount ?? 0).toLocaleString(), count: summaryData.unmatched?.count ? summaryData.unmatched.count.toLocaleString() : "" },
    { label: "Adjustments", amount: (summaryData.exceptions?.amount ?? summaryData.adjustments ?? 0).toLocaleString(), count: summaryData.exceptions?.count ? summaryData.exceptions.count.toLocaleString() : "" },
  ] : [];

  if (isSummaryLoading) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-5 w-72 mt-2" />
        </div>
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-3 gap-6">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <div className="grid grid-cols-3 gap-6">
          <Skeleton className="h-80 col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  // Show empty state if no data available
  if (!summaryData || !summaryData.run_id) {
    return (
      <div className="p-6 space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground">Recon Dashboard (Default Page)</p>
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

        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-yellow-700">
              <AlertCircle className="h-4 w-4" />
              <span>No reconciliation data available yet. Please upload files and run reconciliation to see dashboard data.</span>
            </div>
            <Button 
              className="mt-4 bg-brand-blue hover:bg-brand-mid"
              onClick={() => window.location.href = '/file-upload'}
            >
              Go to File Upload
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Recon Dashboard (Default Page)</p>
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
          <TabsTrigger value="recon" className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground">
            Recon Dashboard
          </TabsTrigger>
          <TabsTrigger value="breaks" className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground">
            Today's Breaks
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
                    <div className="text-3xl font-bold text-green-600">{(summaryData.matched?.count ?? summaryData.matched ?? 0)}</div>
                    <div className="text-sm text-muted-foreground">Transactions Matched</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chart Carousel and Summary */}
          <div className="grid grid-cols-3 gap-6">
            <Card className="col-span-2 shadow-lg">
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
                              <Bar dataKey="allTxns" fill={CHART_COLORS.brandSky} name="All Txns" radius={[6, 6, 0, 0]} />
                              <Bar dataKey="reconciled" fill={CHART_COLORS.matched} name="Reconciled" radius={[6, 6, 0, 0]} />
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
                                stroke={CHART_COLORS.brandSky}
                                strokeWidth={3}
                                name="All Txns"
                                dot={{ fill: CHART_COLORS.brandSky, r: 4 }}
                                activeDot={{ r: 6 }}
                              />
                              <Line
                                type="monotone"
                                dataKey="reconciled"
                                stroke={CHART_COLORS.matched}
                                strokeWidth={3}
                                name="Reconciled"
                                dot={{ fill: CHART_COLORS.matched, r: 4 }}
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
                              <Bar dataKey="successRate" fill={CHART_COLORS.matched} name="Success Rate %" radius={[6, 6, 0, 0]} />
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
                                fill={CHART_COLORS.brandSky}
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
                                  <stop offset="5%" stopColor={CHART_COLORS.matched} stopOpacity={0.8}/>
                                  <stop offset="95%" stopColor={CHART_COLORS.matched} stopOpacity={0.1}/>
                                </linearGradient>
                                <linearGradient id="colorUnmatched" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={CHART_COLORS.unmatched} stopOpacity={0.8}/>
                                  <stop offset="95%" stopColor={CHART_COLORS.unmatched} stopOpacity={0.1}/>
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
                                stroke={CHART_COLORS.matched}
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

            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Array.isArray(summaryDisplayData) && summaryDisplayData.map((item, index) => (
                    <div key={index} className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-sm text-muted-foreground">{item?.label || 'N/A'}</span>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{item?.amount || '0'}</div>
                        {item?.count && <div className="text-xs text-brand-sky">{item.count}</div>}
                      </div>
                    </div>
                  ))}
                  {!Array.isArray(summaryDisplayData) && (
                    <div className="text-sm text-muted-foreground">No summary data available</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <Card className="shadow-lg">
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="flex gap-4 items-end">
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium">Cycle</label>
                    <CycleSelector value={selectedCycle} onValueChange={setSelectedCycle} />
                  </div>
                  
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium">Direction</label>
                    <DirectionSelector value={selectedDirection} onValueChange={setSelectedDirection} />
                  </div>
                </div>

                <div className="flex gap-4 items-end">
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium">Select Date Range</label>
                    <div className="flex gap-2">
                      <input
                        type="date"
                        value={dateFrom}
                        onChange={(e) => setDateFrom(e.target.value)}
                        className="flex-1 px-3 py-2 border rounded-lg bg-background"
                      />
                      <span className="self-center">To</span>
                      <input
                        type="date"
                        value={dateTo}
                        onChange={(e) => setDateTo(e.target.value)}
                        className="flex-1 px-3 py-2 border rounded-lg bg-background"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex gap-4 items-end">
                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium">Select Txn Type</label>
                    <Select value={txnType} onValueChange={setTxnType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="inward">Inward</SelectItem>
                        <SelectItem value="outward">Outward</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex-1 space-y-2">
                    <label className="text-sm font-medium">Select Txn Category</label>
                    <Select value={txnCategory} onValueChange={setTxnCategory}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="success">Success</SelectItem>
                        <SelectItem value="hanging">Hanging</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* KPI Cards */}
          <div className="grid grid-cols-3 gap-6">
            <Card className="bg-gradient-to-br from-brand-light to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Txns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-brand-blue">
                      {summaryData?.total_transactions?.toLocaleString() || '0'}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Latest Run</div>
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
                      {summaryData?.matched?.count?.toLocaleString() ?? summaryData?.matched?.toLocaleString?.() ?? '0'}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Successfully Reconciled</div>
                  </div>
                  <CheckCircle2 className="h-10 w-10 text-green-600 opacity-20" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-red-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Unmatched</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold text-red-600">
                      {summaryData?.unmatched?.count?.toLocaleString() ?? summaryData?.unmatched?.toLocaleString?.() ?? '0'}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Require Attention</div>
                  </div>
                  <AlertCircle className="h-10 w-10 text-red-600 opacity-20" />
                </div>
              </CardContent>
            </Card>
          </div>
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
                    {summaryData?.unmatched?.count ?? summaryData?.unmatched ?? 0}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Breaks to resolve
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {summaryData && (summaryData.unmatched?.count ?? summaryData.unmatched ?? 0) > 0 ? (
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
                          {summaryData.unmatched?.count ?? summaryData.unmatched ?? 0}
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
                          {Math.floor((summaryData.unmatched?.count ?? summaryData.unmatched ?? 0) * 0.6)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Can be force matched</p>
                      </div>
                      <Activity className="h-8 w-8 text-orange-600 opacity-20" />
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="shadow-lg bg-gradient-to-br from-red-50 to-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Orphan Records</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold text-red-600">
                          {Math.floor((summaryData.unmatched?.count ?? summaryData.unmatched ?? 0) * 0.4)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">One-sided transactions</p>
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
                          {(summaryData.totals?.count ?? summaryData.total_transactions ?? 0) > 0 ? Math.round(((summaryData.matched?.count ?? summaryData.matched ?? 0) / (summaryData.totals?.count ?? summaryData.total_transactions ?? 0)) * 100) : 0}%
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
                  <p className="text-sm text-muted-foreground">Today's unmatched transaction breakdown</p>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Partial Matches", value: Math.floor((summaryData.unmatched?.count ?? summaryData.unmatched ?? 0) * 0.6), color: "hsl(39, 100%, 50%)" },
                          { name: "Orphan Records", value: Math.floor((summaryData.unmatched?.count ?? summaryData.unmatched ?? 0) * 0.4), color: "hsl(0, 84%, 60%)" }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={90}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        <Cell fill="hsl(39, 100%, 50%)" />
                        <Cell fill="hsl(0, 84%, 60%)" />
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
      </Tabs>
    </div>
  );
}
