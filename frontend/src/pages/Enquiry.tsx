import React, { useState, useEffect, useRef, ReactNode } from "react";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Send, Search } from "lucide-react";
import { ScrollArea } from "../components/ui/scroll-area";
import { Badge } from "../components/ui/badge";
import { apiClient } from "../lib/api";

interface Message {
  id: number;
  role: "user" | "bot";
  // content can be plain text or a React node for rich bot responses
  content: string | ReactNode;
  timestamp: Date;
}

export default function Enquiry() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "bot",
      content: "Hello! I'm your UPI Reconciliation Assistant. Enter an RRN (12 digits) or Transaction ID to get transaction details.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showSuggestion, setShowSuggestion] = useState(true);
  const [instrOpen, setInstrOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const formatTransactionDetails = (details: any, rrn: string, status: string) => {
    // Build a JSX element with structured sections so the UI renders nicely
    return (
      <div className="space-y-3 w-full">
        <div className="p-3 rounded-md bg-muted">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <div className="text-sm font-semibold">RRN (12-digit Reference)</div>
              <div className="font-mono text-lg font-bold">{rrn || details.rrn || 'N/A'}</div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold">UPI Transaction ID</div>
              <div className="font-mono text-sm">{details.reference || details.upi_tran_id || details.UPI_Tran_ID || 'N/A'}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-semibold">Status</div>
                <div className="font-semibold">
                  {
                    (() => {
                      const s = (status || details.status || 'UNKNOWN').toString().toUpperCase();
                      const classMap: Record<string,string> = {
                        'MATCHED': 'bg-green-500 text-white px-2 py-0.5 rounded-full text-xs',
                        'FULL_MATCH': 'bg-green-500 text-white px-2 py-0.5 rounded-full text-xs',
                        'PARTIAL': 'bg-yellow-400 text-black px-2 py-0.5 rounded-full text-xs',
                        'PARTIAL_MATCH': 'bg-yellow-400 text-black px-2 py-0.5 rounded-full text-xs',
                        'ORPHAN': 'bg-orange-400 text-black px-2 py-0.5 rounded-full text-xs',
                        'MISMATCH': 'bg-red-500 text-white px-2 py-0.5 rounded-full text-xs'
                      };
                      const cls = classMap[s] || 'bg-gray-300 text-black px-2 py-0.5 rounded-full text-xs';
                      return <span className={cls}>{s}</span>;
                    })()
                  }
                </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3 rounded-md bg-white border">
            <div className="text-sm font-semibold mb-2">CBS</div>
            {details.cbs ? (
              <div className="text-xs">
                <div>Amount: ₹{Number(details.cbs.amount || 0).toLocaleString()}</div>
                <div>Date: {details.cbs.date || 'N/A'}</div>
                <div>Dr/Cr: {details.cbs.dr_cr || 'N/A'}</div>
                <div>RC: {details.cbs.rc || 'N/A'}</div>
                <div>Type: {details.cbs.tran_type || 'N/A'}</div>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Not found</div>
            )}
          </div>

          <div className="p-3 rounded-md bg-white border">
            <div className="text-sm font-semibold mb-2">Switch</div>
            {details.switch ? (
              <div className="text-xs">
                <div>Amount: ₹{Number(details.switch.amount || 0).toLocaleString()}</div>
                <div>Date: {details.switch.date || 'N/A'}</div>
                <div>Type: {details.switch.tran_type || 'N/A'}</div>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Not found</div>
            )}
          </div>

          <div className="p-3 rounded-md bg-white border">
            <div className="text-sm font-semibold mb-2">NPCI</div>
            {details.npci ? (
              <div className="text-xs">
                <div>Amount: ₹{Number(details.npci.amount || 0).toLocaleString()}</div>
                <div>Date: {details.npci.date || 'N/A'}</div>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Not found</div>
            )}
          </div>
        </div>

        <div className="p-3 rounded-md bg-white border">
          <div className="text-sm font-semibold mb-2">Recon metadata</div>
          <div className="text-xs">Run: {details.recon_run_id || 'N/A'}</div>
          <div className="text-xs">Direction: {details.direction || 'N/A'}</div>
        </div>

        {/* Related / previous transactions (if present in record) */}
        {(details.previous || details.related || details.related_transactions || details.history) && (
          <div className="p-3 rounded-md bg-white border">
            <div className="text-sm font-semibold mb-2">Related / Previous Transactions</div>
            <div className="text-xs space-y-2">
              {(details.previous || details.related || details.related_transactions || details.history).map((r: any, i: number) => (
                <div key={i} className="p-2 border rounded-sm bg-muted/50">
                  <div className="font-mono text-xs">RRN: {r.rrn || r.RRN || 'N/A'}</div>
                  <div className="text-xs">Status: {r.status || 'N/A'}</div>
                  <div className="text-xs">Amount: ₹{Number(r.amount || r.cbs?.amount || 0).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <details className="p-3 rounded-md bg-white border">
          <summary className="cursor-pointer text-sm font-semibold">Raw record (expand)</summary>
          <pre className="text-xs whitespace-pre-wrap mt-2">{JSON.stringify(details, null, 2)}</pre>
        </details>
      </div>
    );
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    setShowSuggestion(false);
    const userMessage: Message = {
      id: messages.length + 1,
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    const currentInput = input;
    setInput("");
    setIsTyping(true);

    try {
      let response;

      // Detect a 12-digit RRN anywhere in the text (e.g. "hi check rrn 355481530062")
      const rrnMatch = currentInput.match(/\b(\d{12})\b/);
      if (rrnMatch) {
        response = await apiClient.getChatbotByRRN(rrnMatch[1]);
      } else {
        // Detect common TXN id patterns like 'TXN001', 'txn 001', 'transaction 123'
        const txnMatch = currentInput.match(/\b(?:txn[_\- ]?|transaction[_ ]?|trx[_ ]?)(\d+)\b/i);
        if (txnMatch) {
          response = await apiClient.getChatbotByTxnId(txnMatch[1]);
        } else if (/^\d+$/.test(currentInput.trim())) {
          // Pure numeric input -> treat as txn id
          response = await apiClient.getChatbotByTxnId(currentInput.trim());
        } else {
          // No identifier found in text — try sending as-is to txn endpoint (fallback)
          response = await apiClient.getChatbotByTxnId(currentInput.trim());
        }
      }

      const botMessage: Message = {
        id: messages.length + 2,
        role: "bot",
        content: response?.details
          ? formatTransactionDetails(response.details, response.rrn || (rrnMatch ? rrnMatch[1] : currentInput), response.details.status || 'UNKNOWN')
          : `Transaction ${rrnMatch ? rrnMatch[1] : currentInput} not found in the reconciliation data.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: messages.length + 2,
        role: "bot",
        content: `Sorry, I couldn't find information for "${currentInput}". Please try a valid 12-digit RRN or Transaction ID.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    setShowSuggestion(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Transaction Enquiry</h1>
            <p className="text-muted-foreground">Search for transaction details by RRN or Transaction ID</p>
          </div>
          <div className="pt-1">
            <Button onClick={() => setInstrOpen(!instrOpen)} className="px-3">
              Instructions
            </Button>
          </div>
        </div>
      </div>

      <div className={`grid grid-cols-1 ${instrOpen ? 'lg:grid-cols-3' : 'lg:grid-cols-1'} gap-6 transition-all duration-300`}>
        {/* Chat Area */}
        <Card className="lg:col-span-2 shadow-lg">
          <CardContent className="p-0">
            <ScrollArea className="h-[600px] p-6" ref={scrollRef}>
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                  <div
                    className={`max-w-full rounded-lg p-4 ${
                        message.role === "user"
                          ? "bg-brand-blue text-white"
                          : "bg-muted"
                      }`}
                    >
                      {typeof message.content === 'string' ? (
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      ) : (
                        <div className="text-sm">{message.content}</div>
                      )}
                      <p className="text-xs mt-2 opacity-70">
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg p-4">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="border-t p-4">
              {showSuggestion && (
                <div className="mb-3 flex flex-wrap gap-2">
                  <Badge 
                    variant="outline" 
                    className="cursor-pointer hover:bg-brand-blue hover:text-white transition-colors"
                    onClick={() => handleSuggestionClick('355481530062')}
                  >
                    Try: 355481530062
                  </Badge>
                  <Badge 
                    variant="outline" 
                    className="cursor-pointer hover:bg-brand-blue hover:text-white transition-colors"
                    onClick={() => handleSuggestionClick('TXN001')}
                  >
                    Try: TXN001
                  </Badge>
                </div>
              )}
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter RRN (12 digits) or Transaction ID..."
                  className="flex-1"
                  disabled={isTyping}
                />
                <Button
                  onClick={handleSend}
                  disabled={isTyping || !input.trim()}
                  className="bg-brand-blue hover:bg-brand-mid"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {instrOpen && (
          <Card className="shadow-lg">
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  How to Search
                </h3>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p>• Enter a 12-digit RRN number</p>
                  <p>• Or enter a Transaction ID</p>
                  <p>• Press Enter or click Send</p>
                </div>
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Status Indicators</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500">MATCHED</Badge>
                    <span className="text-xs text-muted-foreground">All systems agree</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-yellow-500">PARTIAL</Badge>
                    <span className="text-xs text-muted-foreground">2 systems match</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-orange-500">ORPHAN</Badge>
                    <span className="text-xs text-muted-foreground">Only 1 system</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-red-500">MISMATCH</Badge>
                    <span className="text-xs text-muted-foreground">Data conflict</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}