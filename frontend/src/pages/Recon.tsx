import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Loader2, CheckCircle2, Clock } from "lucide-react";
import { useToast } from "../hooks/use-toast";
import CycleSelector from "../components/CycleSelector";
import DirectionSelector from "../components/DirectionSelector";
import { generateDemoSummary } from "../lib/demoData";

export default function Recon() {
  const { toast } = useToast();
  const [report, setReport] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [reconciliating, setReconciliating] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [selectedCycle, setSelectedCycle] = useState("all");
  const [selectedDirection, setSelectedDirection] = useState("inward");

  useEffect(() => {
    // DEMO MODE: Use demo data directly
    setLoading(true);
    const demoSummary = generateDemoSummary();
    setSummary(demoSummary);
    setReport(`Reconciliation Report
Run ID: ${demoSummary.run_id}
Status: ${demoSummary.status}
Generated: ${demoSummary.generated_at}

=== Summary ===
Total Transactions: ${demoSummary.totals.count.toLocaleString()}
Matched: ${demoSummary.matched.count.toLocaleString()} (${Math.round((demoSummary.matched.count / demoSummary.totals.count) * 100)}%)
Partial Matches: ${demoSummary.partial_matches.count.toLocaleString()} (${Math.round((demoSummary.partial_matches.count / demoSummary.totals.count) * 100)}%)
Hanging: ${demoSummary.hanging.count.toLocaleString()} (${Math.round((demoSummary.hanging.count / demoSummary.totals.count) * 100)}%)
Unmatched: ${demoSummary.unmatched.count.toLocaleString()} (${Math.round((demoSummary.unmatched.count / demoSummary.totals.count) * 100)}%)

This is a demo reconciliation run with simulated data.`);
    setLoading(false);
  }, []);

  const handleRunRecon = async () => {
    try {
      setReconciliating(true);
      // Simulate processing time
      await new Promise((resolve) => setTimeout(resolve, 1500));
      
      toast({
        title: "Reconciliation completed (Demo)",
        description: `Processed reconciliation successfully`,
      });
    } catch (error: any) {
      toast({
        title: "Reconciliation failed",
        description: error.message || "An error occurred during reconciliation",
        variant: "destructive",
      });
    } finally {
      setReconciliating(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Recon Workflow</h1>
        <p className="text-muted-foreground">
          Run reconciliation and view reports
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Status Banner */}
        {summary && summary.run_id && (
          <Card className="shadow-sm bg-gradient-to-r from-blue-50 to-card border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">
                    Current Reconciliation Status
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Run ID: {summary.run_id}
                  </p>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                    <span>Status:</span>
                    {reconciliating ? (
                      <span className="flex items-center gap-1 text-blue-600">
                        <Clock className="h-4 w-4 animate-spin" /> Running...
                      </span>
                    ) : summary.status === "completed" ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle2 className="h-4 w-4" /> Completed
                      </span>
                    ) : (
                      <span>{summary.status}</span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-green-600">
                    {(summary.matched?.count ?? summary.matched ?? 0).toLocaleString()}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Transactions Matched
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Run Reconciliation Section */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-xl">Run Reconciliation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-sm font-medium">Cycle</Label>
                <CycleSelector value={selectedCycle} onValueChange={setSelectedCycle} />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">Direction</Label>
                <DirectionSelector value={selectedDirection} onValueChange={setSelectedDirection} />
              </div>
            </div>
            
            <div className="flex items-center justify-between pt-4 border-t">
              <p className="text-xs text-muted-foreground max-w-[60%]">
                Configure the cycle and direction parameters above to initiate a new reconciliation process.
              </p>
              <Button
                size="sm"
                className="bg-brand-blue hover:bg-brand-mid px-6"
                onClick={handleRunRecon}
                disabled={reconciliating}
              >
                {reconciliating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  "Run Recon"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}