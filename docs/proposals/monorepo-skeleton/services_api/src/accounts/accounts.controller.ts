import { Controller, Post, Body, UseGuards, Request } from '@nestjs/common';
import { JwtAuthGuard } from './auth/jwt-auth.guard';
import { PrismaService } from './prisma.service';
import { CreateAccountDto } from '@finance-os/shared-types';

@Controller('accounts')
export class AccountsController {
  constructor(private prisma: PrismaService) {}

  @UseGuards(JwtAuthGuard)
  @Post()
  async create(@Request() req, @Body() dto: CreateAccountDto) {
    return this.prisma.account.create({
      data: {
        ...dto,
        userId: req.user.id,
      },
    });
  }
}
