import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";
import { AlertCircle, Clock, CheckCircle, FileText, Plus } from "lucide-react";
import { generateDemoDisputes, getDisputeStats } from "../lib/disputeDemoData";
import { Dispute, TxnSubtype, getStageName } from "../types/dispute";
import { getDisputeCategories, getReasonCodes } from "../constants/disputeMaster";
import { useToast } from "../hooks/use-toast";

export default function Disputes() {
  const { toast } = useToast();
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [filteredDisputes, setFilteredDisputes] = useState<Dispute[]>([]);
  const [activeTab, setActiveTab] = useState<"open" | "working" | "closed">("open");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  
  // Create Dispute Form State
  const [txnSubtype, setTxnSubtype] = useState<TxnSubtype>("U2");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedReasonCode, setSelectedReasonCode] = useState("");
  const [transactionRRN, setTransactionRRN] = useState("");
  const [transactionAmount, setTransactionAmount] = useState("");

  useEffect(() => {
    // Load demo disputes
    const demoDisputes = generateDemoDisputes();
    setDisputes(demoDisputes);
    filterDisputes(demoDisputes, activeTab);
  }, []);

  useEffect(() => {
    filterDisputes(disputes, activeTab);
  }, [activeTab, disputes]);

  const filterDisputes = (allDisputes: Dispute[], status: string) => {
    const filtered = allDisputes.filter(d => {
      switch (status) {
        case "open":
          return d.statusGroup === "Open";
        case "working":
          return d.statusGroup === "Working";
        case "closed":
          return d.statusGroup === "Closed";
        default:
          return true;
      }
    });
    setFilteredDisputes(filtered);
  };

  const stats = getDisputeStats(disputes);

  // Get available categories based on selected subtype
  const availableCategories = getDisputeCategories(txnSubtype);

  // Get available reason codes based on selected subtype and category
  const availableReasonCodes = selectedCategory 
    ? getReasonCodes(txnSubtype, selectedCategory)
    : [];

  // Get selected reason code details
  const selectedReasonDetails = availableReasonCodes.find(
    r => r.reasonCode === selectedReasonCode
  );

  const handleCreateDispute = () => {
    if (!selectedReasonCode || !transactionRRN) {
      toast({
        title: "Validation Error",
        description: "Please fill all required fields",
        variant: "destructive"
      });
      return;
    }

    // Create new dispute
    const newDispute: Dispute = {
      disputeId: `DIS${new Date().getFullYear()}${String(new Date().getMonth() + 1).padStart(2, '0')}${String(Math.floor(Math.random() * 10000)).padStart(4, '0')}`,
      txnSubtype: txnSubtype,
      disputeCategory: selectedCategory,
      stageCode: "B", // Always starts at Raise
      reasonCode: selectedReasonCode,
      reasonDescription: selectedReasonDetails?.reasonDescription || "",
      tatDays: selectedReasonDetails?.tatDays || 90,
      tatReference: selectedReasonDetails?.tatReference || "Txn Date",
      statusGroup: "Open",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      transactionRRN: transactionRRN,
      transactionAmount: transactionAmount ? parseFloat(transactionAmount) : undefined,
      transactionDate: new Date().toISOString()
    };

    setDisputes([newDispute, ...disputes]);
    setIsCreateDialogOpen(false);
    
    // Reset form
    setTxnSubtype("U2");
    setSelectedCategory("");
    setSelectedReasonCode("");
    setTransactionRRN("");
    setTransactionAmount("");

    toast({
      title: "Dispute Created (Demo)",
      description: `Dispute ${newDispute.disputeId} has been created successfully`
    });
  };

  const getTATStatusBadge = (dispute: Dispute) => {
    const createdDate = new Date(dispute.createdAt);
    const today = new Date();
    const daysPassed = Math.floor((today.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
    const tatDays = dispute.tatDays;
    
    if (daysPassed >= tatDays) {
      return <Badge variant="destructive">TAT Breached</Badge>;
    } else if (daysPassed >= tatDays * 0.8) {
      return <Badge className="bg-yellow-500">Approaching TAT</Badge>;
    } else {
      return <Badge className="bg-green-500">Within TAT</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dispute Management</h1>
          <p className="text-muted-foreground">NPCI/RBI Compliant Dispute Resolution</p>
        </div>
        
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Create Dispute
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New Dispute</DialogTitle>
              <DialogDescription>
                Enter dispute details based on NPCI dispute master
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Transaction Subtype */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Transaction Subtype *</Label>
                <Select value={txnSubtype} onValueChange={(val) => {
                  setTxnSubtype(val as TxnSubtype);
                  setSelectedCategory("");
                  setSelectedReasonCode("");
                }}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="U2">U2 - Chargeback</SelectItem>
                    <SelectItem value="U3">U3 - Fraud</SelectItem>
                    <SelectItem value="UC">UC - Credit Adjustment</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Dispute Category (Dispute Action) */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Dispute Action *</Label>
                <Select value={selectedCategory} onValueChange={(val) => {
                  setSelectedCategory(val);
                  setSelectedReasonCode("");
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select dispute action" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableCategories.length === 0 ? (
                      <SelectItem value="none" disabled>No actions available</SelectItem>
                    ) : (
                      availableCategories.map(cat => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Select the NPCI dispute action for this transaction
                </p>
              </div>

              {/* Reason Code */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Reason Code *</Label>
                <Select 
                  value={selectedReasonCode} 
                  onValueChange={setSelectedReasonCode}
                  disabled={!selectedCategory}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={!selectedCategory ? "Select category first" : "Select reason code"} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableReasonCodes.length === 0 && selectedCategory ? (
                      <SelectItem value="none" disabled>No reason codes available</SelectItem>
                    ) : (
                      availableReasonCodes.map(reason => (
                        <SelectItem key={reason.reasonCode} value={reason.reasonCode}>
                          {reason.reasonCode} – {reason.reasonDescription}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                {selectedCategory && availableReasonCodes.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    No reason codes found for {txnSubtype} - {selectedCategory}
                  </p>
                )}
              </div>

              {/* Auto-populated fields */}
              {selectedReasonDetails && (
                <div className="space-y-3 p-4 bg-muted/50 rounded-lg">
                  <div>
                    <Label className="text-xs text-muted-foreground">Reason Description</Label>
                    <p className="text-sm font-medium">{selectedReasonDetails.reasonDescription}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-muted-foreground">TAT (Days)</Label>
                      <p className="text-sm font-medium">{selectedReasonDetails.tatDays} days</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">TAT Reference</Label>
                      <p className="text-sm font-medium">{selectedReasonDetails.tatReference}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Transaction Details */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Transaction RRN *</Label>
                <Input 
                  placeholder="Enter RRN"
                  value={transactionRRN}
                  onChange={(e) => setTransactionRRN(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium">Transaction Amount (₹)</Label>
                <Input 
                  type="number"
                  placeholder="0.00"
                  value={transactionAmount}
                  onChange={(e) => setTransactionAmount(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateDispute}>
                Create Dispute
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Disputes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{stats.total}</div>
                <div className="text-xs text-muted-foreground mt-1">All stages</div>
              </div>
              <FileText className="h-8 w-8 text-muted-foreground opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Open</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-orange-600">{stats.byStatus.open}</div>
                <div className="text-xs text-muted-foreground mt-1">Raise/Accept/Represent</div>
              </div>
              <AlertCircle className="h-8 w-8 text-orange-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Working</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-blue-600">{stats.byStatus.working}</div>
                <div className="text-xs text-muted-foreground mt-1">Pre-Arb/Arb/Deferred</div>
              </div>
              <Clock className="h-8 w-8 text-blue-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Closed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-green-600">{stats.byStatus.closed}</div>
                <div className="text-xs text-muted-foreground mt-1">Resolved</div>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* TAT Status Overview */}
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>TAT Compliance Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-2xl font-bold text-green-600">{stats.tatStatus.withinTAT}</div>
              <div className="text-sm text-muted-foreground mt-1">Within TAT</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="text-2xl font-bold text-yellow-600">{stats.tatStatus.approachingTAT}</div>
              <div className="text-sm text-muted-foreground mt-1">Approaching TAT</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="text-2xl font-bold text-red-600">{stats.tatStatus.tatBreached}</div>
              <div className="text-sm text-muted-foreground mt-1">TAT Breached</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dispute Tables by Status */}
      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as any)}>
        <TabsList>
          <TabsTrigger value="open" className="gap-2">
            <AlertCircle className="w-4 h-4" />
            Open ({stats.byStatus.open})
          </TabsTrigger>
          <TabsTrigger value="working" className="gap-2">
            <Clock className="w-4 h-4" />
            Working ({stats.byStatus.working})
          </TabsTrigger>
          <TabsTrigger value="closed" className="gap-2">
            <CheckCircle className="w-4 h-4" />
            Closed ({stats.byStatus.closed})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>
                {activeTab === "open" && "Open Disputes"}
                {activeTab === "working" && "Working Disputes"}
                {activeTab === "closed" && "Closed Disputes"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dispute ID</TableHead>
                    <TableHead>Txn Subtype</TableHead>
                    <TableHead>Dispute Action</TableHead>
                    <TableHead>Reason Code</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>TAT</TableHead>
                    <TableHead>TAT Status</TableHead>
                    <TableHead>RRN</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDisputes.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        No {activeTab} disputes found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredDisputes.map((dispute) => (
                      <TableRow key={dispute.disputeId}>
                        <TableCell className="font-medium">{dispute.disputeId}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{dispute.txnSubtype}</Badge>
                        </TableCell>
                        <TableCell>{dispute.disputeCategory}</TableCell>
                        <TableCell className="font-mono text-xs">{dispute.reasonCode}</TableCell>
                        <TableCell className="max-w-xs truncate" title={dispute.reasonDescription}>
                          {dispute.reasonDescription}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{getStageName(dispute.stageCode)}</Badge>
                        </TableCell>
                        <TableCell className="text-xs">
                          {dispute.tatDays} days from {dispute.tatReference}
                        </TableCell>
                        <TableCell>
                          {getTATStatusBadge(dispute)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{dispute.transactionRRN}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}