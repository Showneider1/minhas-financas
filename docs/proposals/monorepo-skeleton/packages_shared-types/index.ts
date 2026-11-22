import { Account, Transaction, LedgerEntry } from '@finance-os/financial-core';

export interface CreateAccountDto {
  name: string;
  type: Account['type'];
  currency: string;
}

export interface CreateTransactionDto {
  type: Transaction['type'];
  description: string;
  date: Date;
  entries: {
    accountId: string;
    amount: number;
    type: LedgerEntry['type'];
  }[];
}

export interface AuthResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
  };
}
