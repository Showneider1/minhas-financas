import { Controller, Post, Body, UseGuards, Request, BadRequestException } from '@nestjs/common';
import { JwtAuthGuard } from './auth/jwt-auth.guard';
import { PrismaService } from './prisma.service';
import { CreateTransactionDto } from '@finance-os/shared-types';
import { validateTransactionBalance } from '@finance-os/financial-core';

@Controller('transactions')
export class TransactionsController {
  constructor(private prisma: PrismaService) {}

  @UseGuards(JwtAuthGuard)
  @Post()
  async create(@Request() req, @Body() dto: CreateTransactionDto) {
    // 1. Validate Ledger Balance
    const entriesForValidation = dto.entries.map(e => ({
      amount: e.amount,
      type: e.type
    }));
    
    if (!validateTransactionBalance(entriesForValidation as any)) {
      throw new BadRequestException('Transaction must balance (Debits == Credits)');
    }

    // 2. Atomic Transaction
    return this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          userId: req.user.id,
          type: dto.type,
          description: dto.description,
          date: dto.date,
          entries: {
            create: dto.entries
          }
        }
      });
      return transaction;
    });
  }
}
