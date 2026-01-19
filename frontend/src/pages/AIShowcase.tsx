import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { 
  Sparkles, 
  Brain, 
  MessageSquare, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  Globe
} from "lucide-react";

// Mock AI data
const AI_INSIGHTS = {
  matchSuggestions: [
    {
      rrn: "636397811101710",
      confidence: 92,
      suggestedMatch: "TXN001240",
      reasons: [
        "Amount exact match (₹12,300.00)",
        "Date match (2026-01-13)",
        "Reference number similarity (98%)",
        "Historical pattern match"
      ],
      featureWeights: {
        amount: 35,
        date: 25,
        reference: 30,
        pattern: 10
      }
    },
    {
      rrn: "636397811101711",
      confidence: 87,
      suggestedMatch: "TXN001245",
      reasons: [
        "Amount match within tolerance",
        "Same transaction date",
        "Customer pattern recognized"
      ],
      featureWeights: {
        amount: 40,
        date: 30,
        customer: 30
      }
    }
  ],
  clusters: [
    {
      id: "CL001",
      type: "Recurring Pattern",
      count: 23,
      pattern: "Missing CBS entries during 2-3 PM window",
      action: "Check CBS batch processing schedule",
      priority: "high"
    },
    {
      id: "CL002",
      type: "Settlement Delay",
      count: 15,
      pattern: "NPCI settlement delay for specific merchant",
      action: "Flag for manual review",
      priority: "medium"
    }
  ]
};

export default function AIShowcase() {
  const [selectedLanguage, setSelectedLanguage] = useState("en");

  return (
    <div className="p-6 space-y-6">
      {/* Header with Advisory Badge */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-brand-purple" />
              AI Showcase
            </h1>
            <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
              Preview Only
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Preview of Upcoming AI Capabilities (Advisory Only)
          </p>
        </div>
      </div>

      <Tabs defaultValue="match-confidence" className="w-full">
        <TabsList className="bg-muted/30">
          <TabsTrigger value="match-confidence">
            <Brain className="w-4 h-4 mr-2" />
            Match Confidence
          </TabsTrigger>
          <TabsTrigger value="clustering">
            <TrendingUp className="w-4 h-4 mr-2" />
            Exception Clustering
          </TabsTrigger>
          <TabsTrigger value="chatbot">
            <MessageSquare className="w-4 h-4 mr-2" />
            Ask Verif.AI
          </TabsTrigger>
        </TabsList>

        {/* AI Match Confidence Tab */}
        <TabsContent value="match-confidence" className="space-y-4 mt-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>AI-Powered Matching:</strong> Our AI analyzes multiple features to suggest potential matches for unmatched transactions with explainable confidence scores.
            </p>
          </div>

          {AI_INSIGHTS.matchSuggestions.map((suggestion, idx) => (
            <Card key={idx} className="border-2">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">RRN: {suggestion.rrn}</CardTitle>
                    <CardDescription>Suggested Match: {suggestion.suggestedMatch}</CardDescription>
                  </div>
                  <Badge 
                    variant={suggestion.confidence >= 90 ? "default" : "secondary"}
                    className="text-base px-3 py-1"
                  >
                    {suggestion.confidence}% Confidence
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Confidence Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Match Confidence</span>
                    <span className="font-medium">{suggestion.confidence}%</span>
                  </div>
                  <Progress value={suggestion.confidence} className="h-2" />
                </div>

                {/* Reasons */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Reasoning:</h4>
                  <div className="space-y-1">
                    {suggestion.reasons.map((reason, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Feature Weights */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Feature Weights:</h4>
                  <div className="space-y-1">
                    {Object.entries(suggestion.featureWeights).map(([feature, weight]) => (
                      <div key={feature} className="flex items-center gap-2">
                        <div className="w-24 text-sm text-muted-foreground capitalize">{feature}</div>
                        <Progress value={weight as number} className="h-1.5 flex-1" />
                        <div className="w-12 text-sm text-right">{weight}%</div>
                      </div>
                    ))}
                  </div>
                </div>

                <Button variant="outline" className="w-full" disabled>
                  Apply Suggestion (Coming Soon)
                </Button>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Exception Clustering Tab */}
        <TabsContent value="clustering" className="space-y-4 mt-6">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <p className="text-sm text-orange-900">
              <strong>Smart Grouping:</strong> AI identifies patterns in exceptions and clusters similar issues together for efficient resolution.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {AI_INSIGHTS.clusters.map((cluster) => (
              <Card key={cluster.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{cluster.type}</CardTitle>
                      <CardDescription className="text-xs">{cluster.id}</CardDescription>
                    </div>
                    <Badge 
                      variant={cluster.priority === "high" ? "destructive" : "secondary"}
                      className="text-xs"
                    >
                      {cluster.count} cases
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <div className="text-sm font-medium">Pattern Detected:</div>
                    <div className="text-sm text-muted-foreground">{cluster.pattern}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm font-medium">Suggested Action:</div>
                    <div className="text-sm text-muted-foreground">{cluster.action}</div>
                  </div>
                  <div className="flex items-center gap-2 pt-2">
                    <AlertCircle className={`w-4 h-4 ${cluster.priority === "high" ? "text-red-600" : "text-orange-600"}`} />
                    <span className="text-xs font-medium capitalize">{cluster.priority} Priority</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Chatbot Tab */}
        <TabsContent value="chatbot" className="space-y-4 mt-6">
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <p className="text-sm text-purple-900">
              <strong>Ask Verif.AI:</strong> Intelligent chatbot for transaction queries, dispute guidance, and system FAQs with multilingual support.
            </p>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Chatbot Features</CardTitle>
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-muted-foreground" />
                  <select 
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="text-sm border rounded px-2 py-1"
                  >
                    <option value="en">English</option>
                    <option value="hi">हिंदी</option>
                    <option value="ta">தமிழ்</option>
                    <option value="te">తెలుగు</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-brand-blue" />
                    <h4 className="font-medium">FAQ Support</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Instant answers to frequently asked questions about reconciliation processes
                  </p>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-brand-blue" />
                    <h4 className="font-medium">Enquiry</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Step-by-step guidance for resolving disputes and exceptions
                  </p>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-brand-blue" />
                    <h4 className="font-medium">Status Queries</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Real-time transaction status and reconciliation progress
                  </p>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Globe className="w-5 h-5 text-brand-blue" />
                    <h4 className="font-medium">Multilingual</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Support for multiple Indian languages for better accessibility
                  </p>
                </div>
              </div>

              <div className="bg-muted/30 rounded-lg p-4 space-y-2">
                <h4 className="text-sm font-medium">Example Queries:</h4>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div>• "How do I reconcile a transaction?"</div>
                  <div>• "What is a hanging transaction?"</div>
                  <div>• "How to resolve amount mismatch?"</div>
                  <div>• "Show status of RRN 636397811101708"</div>
                </div>
              </div>

              <Button variant="outline" className="w-full" disabled>
                Launch Chatbot (Coming Soon)
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}