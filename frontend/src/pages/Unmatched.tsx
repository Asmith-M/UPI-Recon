import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Loader2, Download, X } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import CycleSelector from "../components/CycleSelector";
import DirectionSelector from "../components/DirectionSelector";
import { exportToCSV } from "../lib/utils";

export default function Unmatched() {
  const { toast } = useToast();
  const [unmatchedNPCI, setUnmatchedNPCI] = useState<any[]>([]);
  const [unmatchedCBS, setUnmatchedCBS] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [amountFrom, setAmountFrom] = useState("");
  const [amountTo, setAmountTo] = useState("");
  const [selectedCycle, setSelectedCycle] = useState("all");
  const [selectedDirection, setSelectedDirection] = useState("all");

  useEffect(() => {
    fetchUnmatchedData();
  }, []);

  const fetchUnmatchedData = async () => {
    try {
      setLoading(true);
      const report = await apiClient.getReport("unmatched");
      
      // Transform the data into unmatched format
      const transformed = transformReportToUnmatched(report.data || {});
      setUnmatchedNPCI(transformed.npci);
      setUnmatchedCBS(transformed.cbs);
    } catch (error: any) {
      console.log("Error fetching unmatched data:", error.message);
      setUnmatchedNPCI([]);
      setUnmatchedCBS([]);
    } finally {
      setLoading(false);
    }
  };

  const transformReportToUnmatched = (data: any) => {
    const npci: any[] = [];
    const cbs: any[] = [];

    // Convert raw data into table format
    Object.entries(data).forEach(([rrn, record]: [string, any]) => {
      // Determine which system is missing based on status
      const hasCBS = record.cbs !== null && record.cbs !== undefined;
      const hasSwitch = record.switch !== null && record.switch !== undefined;
      const hasNPCI = record.npci !== null && record.npci !== undefined;

      // Create transaction object
      const createTransaction = (sourceData: any, sourceName: string) => {
        if (!sourceData) return null;
        
        return {
          source: sourceName,
          rrn: rrn,
          drCr: sourceData.dr_cr || "Dr",
          amount: sourceData.amount || 0,
          amountFormatted: `₹${sourceData.amount?.toLocaleString() || 0}`,
          tranDate: sourceData.date || new Date().toLocaleDateString(),
          rc: sourceData.rc || "00",
          type: sourceData.tran_type || "UPI"
        };
      };

      // Add to NPCI list if NPCI data exists but CBS is missing
      if (hasNPCI && !hasCBS) {
        const transaction = createTransaction(record.npci, "NPCI");
        if (transaction) npci.push(transaction);
      }

      // Add to CBS list if CBS data exists but NPCI is missing
      if (hasCBS && !hasNPCI) {
        const transaction = createTransaction(record.cbs, "CBS");
        if (transaction) cbs.push(transaction);
      }

      // Also add if it's a mismatch or partial match
      if (record.status === 'PARTIAL_MATCH' || record.status === 'MISMATCH' || record.status === 'ORPHAN') {
        if (hasNPCI) {
          const transaction = createTransaction(record.npci, "NPCI");
          if (transaction && !npci.some(t => t.rrn === rrn)) npci.push(transaction);
        }
        if (hasCBS) {
          const transaction = createTransaction(record.cbs, "CBS");
          if (transaction && !cbs.some(t => t.rrn === rrn)) cbs.push(transaction);
        }
      }
    });

    return { npci, cbs };
  };

  // Helper function to parse and format dates for comparison
  const parseDate = (dateString: string): Date | null => {
    if (!dateString) return null;
    // Try parsing DD/MM/YYYY format
    const parts = dateString.split('/');
    if (parts.length === 3) {
      const date = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
      return isNaN(date.getTime()) ? null : date;
    }
    // Try YYYY-MM-DD format
    const date = new Date(dateString);
    return isNaN(date.getTime()) ? null : date;
  };

  // Helper function to check if transaction matches all filters
  const matchesFilters = (row: any): boolean => {
    // RRN search
    if (searchTerm && !row.rrn.toUpperCase().includes(searchTerm.toUpperCase())) {
      return false;
    }

    // Date range filter
    if (dateFrom || dateTo) {
      const tranDate = parseDate(row.tranDate);
      const fromDate = dateFrom ? new Date(dateFrom) : null;
      const toDate = dateTo ? new Date(dateTo) : null;

      if (tranDate) {
        if (fromDate && tranDate < fromDate) return false;
        if (toDate && tranDate > toDate) return false;
      }
    }

    // Transaction type filter
    if (typeFilter !== "all" && row.type.toLowerCase() !== typeFilter.toLowerCase()) {
      return false;
    }

    // Amount range filter
    if (amountFrom && row.amount < parseFloat(amountFrom)) {
      return false;
    }
    if (amountTo && row.amount > parseFloat(amountTo)) {
      return false;
    }

    return true;
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setDateFrom("");
    setDateTo("");
    setTypeFilter("all");
    setAmountFrom("");
    setAmountTo("");
    setSelectedCycle("all");
    setSelectedDirection("all");
    toast({
      title: "Filters cleared",
      description: "All filters have been reset"
    });
  };

  const handleExportCSV = (data: any[], filename: string) => {
    const csvData = data.map(row => ({
      Source: row.source,
      RRN: row.rrn,
      "Dr/Cr": row.drCr,
      Amount: row.amount,
      "Transaction Date": row.tranDate,
      RC: row.rc,
      Type: row.type
    }));
    exportToCSV(csvData, filename);
    toast({
      title: "Export successful",
      description: `${filename} has been downloaded`
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Unmatched Dashboard</h1>
        <p className="text-muted-foreground">View and manage unmatched transactions with advanced filtering</p>
      </div>

      {/* Filters */}
      <Card className="shadow-lg">
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* First row: Cycle and Direction */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Cycle</label>
                <CycleSelector value={selectedCycle} onValueChange={setSelectedCycle} />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Direction</label>
                <DirectionSelector value={selectedDirection} onValueChange={setSelectedDirection} />
              </div>
            </div>

            {/* Second row: RRN search and date range */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                <label className="text-sm font-medium mb-2 block">Search by RRN</label>
                <Input
                  placeholder="Enter RRN..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Date From</label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Date To</label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>

            {/* Third row: Transaction type and amount range */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Transaction Type</label>
                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="upi">UPI</SelectItem>
                    <SelectItem value="p2p">P2P</SelectItem>
                    <SelectItem value="p2m">P2M</SelectItem>
                    <SelectItem value="neft">NEFT</SelectItem>
                    <SelectItem value="imps">IMPS</SelectItem>
                    <SelectItem value="rtgs">RTGS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Amount From (₹)</label>
                <Input
                  type="number"
                  placeholder="0"
                  value={amountFrom}
                  onChange={(e) => setAmountFrom(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Amount To (₹)</label>
                <Input
                  type="number"
                  placeholder="999999999"
                  value={amountTo}
                  onChange={(e) => setAmountTo(e.target.value)}
                />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 justify-end pt-2">
              <Button 
                variant="outline"
                className="rounded-full"
                onClick={handleClearFilters}
              >
                Clear All
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for NPCI and CBS */}
      <Tabs defaultValue="npci" className="w-full">
        <TabsList className="bg-muted/30">
          <TabsTrigger 
            value="npci"
            className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground"
          >
            NPCI Unmatched ({unmatchedNPCI.length})
          </TabsTrigger>
          <TabsTrigger 
            value="cbs"
            className="data-[state=active]:bg-brand-blue data-[state=active]:text-primary-foreground"
          >
            CBS Unmatched ({unmatchedCBS.length})
          </TabsTrigger>
        </TabsList>

        {/* NPCI Unmatched */}
        <TabsContent value="npci">
          <Card className="shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>NPCI Unmatched Transactions</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2"
                  onClick={() => handleExportCSV(unmatchedNPCI.filter(matchesFilters), 'npci_unmatched.csv')}
                  disabled={unmatchedNPCI.filter(matchesFilters).length === 0}
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
                </div>
              ) : unmatchedNPCI.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No unmatched NPCI transactions found</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Source</TableHead>
                      <TableHead>RRN</TableHead>
                      <TableHead>Dr/Cr</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Tran Date</TableHead>
                      <TableHead>RC</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {unmatchedNPCI
                      .filter(matchesFilters)
                      .map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.source}</TableCell>
                          <TableCell>{row.rrn}</TableCell>
                          <TableCell>
                            <span className={row.drCr === "Dr" ? "text-red-600" : "text-green-600"}>
                              {row.drCr}
                            </span>
                          </TableCell>
                          <TableCell className="font-semibold">{row.amountFormatted}</TableCell>
                          <TableCell>{row.tranDate}</TableCell>
                          <TableCell>{row.rc}</TableCell>
                          <TableCell>{row.type}</TableCell>
                          <TableCell>
                            <Button variant="outline" size="sm" className="rounded-full">
                              Match
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* CBS Unmatched */}
        <TabsContent value="cbs">
          <Card className="shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>CBS Unmatched Transactions</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2"
                  onClick={() => handleExportCSV(unmatchedCBS.filter(matchesFilters), 'cbs_unmatched.csv')}
                  disabled={unmatchedCBS.filter(matchesFilters).length === 0}
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
                </div>
              ) : unmatchedCBS.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No unmatched CBS transactions found</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Source</TableHead>
                      <TableHead>RRN</TableHead>
                      <TableHead>Dr/Cr</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Tran Date</TableHead>
                      <TableHead>RC</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {unmatchedCBS
                      .filter(matchesFilters)
                      .map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.source}</TableCell>
                          <TableCell>{row.rrn}</TableCell>
                          <TableCell>
                            <span className={row.drCr === "Dr" ? "text-red-600" : "text-green-600"}>
                              {row.drCr}
                            </span>
                          </TableCell>
                          <TableCell className="font-semibold">{row.amountFormatted}</TableCell>
                          <TableCell>{row.tranDate}</TableCell>
                          <TableCell>{row.rc}</TableCell>
                          <TableCell>{row.type}</TableCell>
                          <TableCell>
                            <Button variant="outline" size="sm" className="rounded-full">
                              Match
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
