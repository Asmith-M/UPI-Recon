import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Loader2 } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";

export default function Unmatched() {
  const { toast } = useToast();
  const [unmatchedNPCI, setUnmatchedNPCI] = useState<any[]>([]);
  const [unmatchedCBS, setUnmatchedCBS] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

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
          amount: `₹${sourceData.amount?.toLocaleString() || 0}`,
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

  const handleApplyFilters = () => {
    // Filters are applied dynamically when user types or selects
    toast({
      title: "Filters applied",
      description: "Data filtered successfully"
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Unmatched Dashboard</h1>
        <p className="text-muted-foreground">View and manage unmatched transactions</p>
      </div>

      {/* Filters */}
      <Card className="shadow-lg">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search by RRN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <Input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Transaction Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="p2p">P2P</SelectItem>
                  <SelectItem value="p2m">P2M</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button 
              className="rounded-full bg-brand-blue hover:bg-brand-mid"
              onClick={handleApplyFilters}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                "Apply Filters"
              )}
            </Button>
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
              <CardTitle>NPCI Unmatched Transactions</CardTitle>
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
                      .filter(row => 
                        (!searchTerm || row.rrn.includes(searchTerm)) &&
                        (!dateFilter || row.tranDate === dateFilter) &&
                        (typeFilter === "all" || row.type.toLowerCase() === typeFilter.toLowerCase())
                      )
                      .map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.source}</TableCell>
                          <TableCell>{row.rrn}</TableCell>
                          <TableCell>
                            <span className={row.drCr === "Dr" ? "text-red-600" : "text-green-600"}>
                              {row.drCr}
                            </span>
                          </TableCell>
                          <TableCell className="font-semibold">{row.amount}</TableCell>
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
              <CardTitle>CBS Unmatched Transactions</CardTitle>
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
                      .filter(row => 
                        (!searchTerm || row.rrn.includes(searchTerm)) &&
                        (!dateFilter || row.tranDate === dateFilter) &&
                        (typeFilter === "all" || row.type.toLowerCase() === typeFilter.toLowerCase())
                      )
                      .map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.source}</TableCell>
                          <TableCell>{row.rrn}</TableCell>
                          <TableCell>
                            <span className={row.drCr === "Dr" ? "text-red-600" : "text-green-600"}>
                              {row.drCr}
                            </span>
                          </TableCell>
                          <TableCell className="font-semibold">{row.amount}</TableCell>
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
