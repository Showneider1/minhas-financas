export type TransactionType = 'INCOME' | 'EXPENSE' | 'TRANSFER';

export interface LedgerEntry {
  id: string;
  transactionId: string;
  accountId: string;
  amount: number; // Always positive for debits, negative for credits (or vice-versa, must be consistent)
  type: 'DEBIT' | 'CREDIT';
  createdAt: Date;
}

export interface Transaction {
  id: string;
  userId: string;
  type: TransactionType;
  description: string;
  date: Date;
  entries: LedgerEntry[];
  metadata?: Record<string, any>;
}

export interface Account {
  id: string;
  userId: string;
  name: string;
  type: 'CHECKING' | 'SAVINGS' | 'INVESTMENT' | 'CASH';
  currency: string;
  createdAt: Date;
}

export function calculateBalance(entries: LedgerEntry[]): number {
  return entries.reduce((sum, entry) => {
    return entry.type === 'DEBIT' ? sum + entry.amount : sum - entry.amount;
  }, 0);
}

export function validateTransactionBalance(entries: LedgerEntry[]): boolean {
  const total = entries.reduce((sum, entry) => {
    return entry.type === 'DEBIT' ? sum + entry.amount : sum - entry.amount;
  }, 0);
  return Math.abs(total) < 0.0001; // Use epsilon for float, though we should use Decimal.js
}
