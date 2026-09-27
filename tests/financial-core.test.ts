import { validateTransactionBalance, calculateBalance } from '@finance-os/financial-core';

describe('Financial Core Logic', () => {
  test('should validate a balanced transaction', () => {
    const entries = [
      { amount: 100, type: 'DEBIT' },
      { amount: 100, type: 'CREDIT' },
    ];
    expect(validateTransactionBalance(entries)).toBe(true);
  });

  test('should invalidate an unbalanced transaction', () => {
    const entries = [
      { amount: 100, type: 'DEBIT' },
      { amount: 50, type: 'CREDIT' },
    ];
    expect(validateTransactionBalance(entries)).toBe(false);
  });

  test('should calculate account balance correctly', () => {
    const entries = [
      { amount: 100, type: 'DEBIT' },
      { amount: 30, type: 'CREDIT' },
      { amount: 20, type: 'CREDIT' },
    ];
    expect(calculateBalance(entries)).toBe(50);
  });
});
