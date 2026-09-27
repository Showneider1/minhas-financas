import { Controller, Post, Body } from '@nestjs/common';
import { PrismaService } from './prisma.service';
import { AuthResponse } from '@finance-os/shared-types';
import * as jwt from 'jsonwebtoken';
import * as bcrypt from 'bcryptjs';

@Controller('auth')
export class AuthController {
  constructor(private prisma: PrismaService) {}

  @Post('signup')
  async signup(@Body() body: any) {
    const hashedPassword = await bcrypt.hash(body.password, 10);
    const user = await this.prisma.user.create({
      data: { email: body.email, password: hashedPassword }
    });
    
    const token = jwt.sign({ id: user.id, email: user.email }, process.env.JWT_SECRET);
    return { accessToken: token, user: { id: user.id, email: user.email } };
  }

  @Post('login')
  async login(@Body() body: any) {
    const user = await this.prisma.user.findUnique({ where: { email: body.email } });
    if (!user || !(await bcrypt.compare(body.password, user.password))) {
      throw new UnauthorizedException();
    }
    const token = jwt.sign({ id: user.id, email: user.email }, process.env.JWT_SECRET);
    return { accessToken: token, user: { id: user.id, email: user.email } };
  }
}
