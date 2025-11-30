import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar
} from "recharts";
import { RefreshCw, AlertCircle, CheckCircle } from "lucide-react";
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

const CHART_COLORS = ["hsl(142, 76%, 36%)", "hsl(0, 84%, 60%)", "hsl(45, 93%, 47%)"];

export default function Dashboard() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [txnType, setTxnType] = useState("all");
  const [txnCategory, setTxnCategory] = useState("all");
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
    { name: "Matched", value: summaryData.matched, color: "hsl(142, 76%, 36%)" },
    { name: "Unmatched", value: summaryData.unmatched, color: "hsl(0, 84%, 60%)" },
  ] : [];

  // Prepare summary display data
  const summaryDisplayData = summaryData ? [
    { label: "Total Transactions", amount: summaryData.total_transactions.toLocaleString(), count: "" },
    { label: "Matched", amount: summaryData.matched.toLocaleString(), count: "" },
    { label: "Unmatched", amount: summaryData.unmatched.toLocaleString(), count: "" },
    { label: "Adjustments", amount: summaryData.adjustments.toLocaleString(), count: "" },
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
              onClick={() => window.location.href = '/upload'}
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
                    <p className="text-sm text-muted-foreground">Status: {summaryData.status === 'completed' ? '✓ Completed' : summaryData.status}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-green-600">{summaryData.matched}</div>
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
                <CardTitle>Analytics Overview</CardTitle>
                <p className="text-sm text-muted-foreground">Swipe or use arrows to view different charts</p>
              </CardHeader>
              <CardContent className="px-4">
                <Carousel className="w-full max-w-full">
                  <CarouselContent className="-ml-2">
                    {/* Pie Chart */}
                    <CarouselItem className="pl-2">
                      <div className="p-1">
                        <h3 className="text-center font-semibold mb-2 text-foreground">Transaction Distribution</h3>
                        <ResponsiveContainer width="100%" height={260}>
                          <PieChart>
                            <Pie
                              data={pieData.length > 0 ? pieData : [{ name: "No Data", value: 1, color: "#ccc" }]}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={90}
                              paddingAngle={5}
                              dataKey="value"
                              label={pieData.length > 0 ? ({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%` : undefined}
                            >
                              {(pieData.length > 0 ? pieData : [{ name: "No Data", value: 1, color: "#ccc" }]).map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip />
                            {pieData.length > 0 && <Legend />}
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Bar Chart */}
                    <CarouselItem className="pl-2">
                      <div className="p-1">
                        <h3 className="text-center font-semibold mb-2 text-foreground">Monthly Comparison</h3>
                        <ResponsiveContainer width="100%" height={260}>
                          <BarChart data={historicalData && historicalData.length > 0 ? historicalData : []}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="allTxns" fill="hsl(201, 78%, 70%)" name="All Txns" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="reconciled" fill="hsl(142, 76%, 36%)" name="Reconciled" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>

                    {/* Line Chart (Trend) */}
                    <CarouselItem className="pl-2">
                      <div className="p-1">
                        <h3 className="text-center font-semibold mb-2 text-foreground">Monthly Trend</h3>
                        <ResponsiveContainer width="100%" height={260}>
                          <LineChart data={historicalData && historicalData.length > 0 ? historicalData : []}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line
                              type="monotone"
                              dataKey="allTxns"
                              stroke="hsl(201, 78%, 70%)"
                              strokeWidth={2}
                              name="All Txns"
                              dot={{ fill: "hsl(201, 78%, 70%)" }}
                            />
                            <Line
                              type="monotone"
                              dataKey="reconciled"
                              stroke="hsl(142, 76%, 36%)"
                              strokeWidth={2}
                              name="Reconciled"
                              dot={{ fill: "hsl(142, 76%, 36%)" }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CarouselItem>
                  </CarouselContent>
                  <CarouselPrevious className="left-2" />
                  <CarouselNext className="right-2" />
                </Carousel>
              </CardContent>
            </Card>

            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {summaryDisplayData.map((item, index) => (
                    <div key={index} className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-sm text-muted-foreground">{item.label}</span>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{item.amount}</div>
                        {item.count && <div className="text-xs text-brand-sky">{item.count}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <Card className="shadow-lg">
            <CardContent className="pt-6">
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
            </CardContent>
          </Card>

          {/* KPI Cards */}
          <div className="grid grid-cols-3 gap-6">
            <Card className="bg-gradient-to-br from-brand-light to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Txns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-foreground">
                  {summaryData?.total_transactions?.toLocaleString() || '0'}
                </div>
                <div className="text-sm text-muted-foreground">Latest Run</div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-green-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Matched</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {summaryData?.matched?.toLocaleString() || '0'}
                </div>
                <div className="text-sm text-muted-foreground">Successfully Reconciled</div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-red-50 to-card shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Unmatched</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {summaryData?.unmatched?.toLocaleString() || '0'}
                </div>
                <div className="text-sm text-muted-foreground">Require Attention</div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Today's Breaks Tab */}
        <TabsContent value="breaks" className="space-y-6 mt-6">
          {summaryData && summaryData.unmatched > 0 ? (
            <>
              <Card className="shadow-lg">
                <CardHeader>
                  <CardTitle>Today's Unmatched Transactions</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Transactions that require attention from today's reconciliation run
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="bg-yellow-50">
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-yellow-600">
                          {summaryData.unmatched}
                        </div>
                        <div className="text-sm text-muted-foreground">Total Breaks</div>
                      </CardContent>
                    </Card>
                    
                    <Card className="bg-orange-50">
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-orange-600">
                          {Math.floor(summaryData.unmatched * 0.6)}
                        </div>
                        <div className="text-sm text-muted-foreground">Partial Matches</div>
                      </CardContent>
                    </Card>
                    
                    <Card className="bg-red-50">
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-red-600">
                          {Math.floor(summaryData.unmatched * 0.4)}
                        </div>
                        <div className="text-sm text-muted-foreground">Orphan Records</div>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="mt-6 flex justify-center">
                    <Button 
                      className="rounded-full bg-brand-blue hover:bg-brand-mid"
                      onClick={() => window.location.href = '/unmatched'}
                    >
                      View Unmatched Dashboard
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle>Today's Breaks</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 mx-auto text-green-500 mb-4" />
                  <p className="text-lg font-semibold text-green-600">No Breaks Today!</p>
                  <p className="text-muted-foreground mt-2">
                    All transactions have been successfully reconciled.
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
