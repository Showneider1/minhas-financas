"""
TIBIA 8.60 - LOGIN AUTOMÁTICO
Versão com tempo para focar cliente manualmente
Baseado em: github.com/ianobermiller/tibiaapi
"""

import time
from pymem import Pymem
import pyautogui
import win32gui
import win32con
import psutil

class TibiaLogin860Final:
    """
    Login automático com foco manual do cliente
    Endereços oficiais TibiaAPI Tibia 8.60
    """

    # ========================================================================
    # ENDEREÇOS OFICIAIS TIBIAAPI - TIBIA 8.60
    # Source: github.com/ianobermiller/tibiaapi/.../Version860.cs
    # ========================================================================

    # Client.LoginPassword = 0x79CEE4
    # Client.LoginAccount = Client.LoginPassword + 32  (= 0x79CF04)
    LOGIN_PASSWORD = 0x79CEE4
    LOGIN_ACCOUNT = 0x79CF04
    LOGIN_CHAR_LIST_LENGTH = 0x79CEE0
    LOGIN_SELECTED_CHAR = 0x79CED8

    # Player (já confirmados como funcionais)
    PLAYER_ID = 0x63FE98
    PLAYER_HEALTH = 0x63FE94
    PLAYER_MAX_HEALTH = 0x63FE90
    PLAYER_LEVEL = 0x63FE88
    PLAYER_NAME = 0x63FE6C
    PLAYER_MANA = 0x63FE9C
    PLAYER_MAX_MANA = 0x63FEA0

    def __init__(self, account: str, password: str, char_index: int = 0):
        self.account = account
        self.password = password
        self.char_index = char_index
        self.pm = None
        self.hwnd = None
        self.process_name = None

    def find_client_process(self) -> bool:
        """Encontra processo do cliente"""
        print("🔍 Procurando Kaldrox/Tibia...\n")

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                if 'kaldrox' in proc_name.lower() or 'tibia' in proc_name.lower():
                    self.process_name = proc_name
                    print(f"✓ {proc_name} (PID: {proc.info['pid']})")
                    return True
            except:
                pass

        print("✗ Cliente não encontrado")
        return False

    def connect(self) -> bool:
        """Conecta ao processo"""
        try:
            if not self.process_name:
                if not self.find_client_process():
                    return False

            print(f"\n🔗 Conectando: {self.process_name}")
            self.pm = Pymem(self.process_name)
            print(f"✓ Conectado (PID: {self.pm.process_id})")

            self._find_window()
            return True

        except Exception as e:
            print(f"✗ Erro: {e}")
            return False

    def _find_window(self):
        """Encontra janela DO JOGO (ignora VS Code, CMD, etc)"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                title_lower = title.lower()

                # Ignora janelas do sistema/desenvolvimento
                ignore_list = ['visual studio', 'vscode', 'cmd', 'powershell', 
                               'python', 'console', 'administrator']

                if any(ignore in title_lower for ignore in ignore_list):
                    return True

                # Procura janela do jogo
                game_keywords = ['kaldrox', 'tibia', 'otclient']
                if any(keyword in title_lower for keyword in game_keywords):
                    windows.append((hwnd, title))

            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.hwnd = windows[0][0]
            print(f"✓ Janela do jogo: '{windows[0][1]}'")
        else:
            print(f"⚠ Janela do jogo não encontrada automaticamente")
            print(f"   Você precisará focar manualmente!")

    def focus_window_auto(self):
        """Tenta focar janela automaticamente"""
        if self.hwnd:
            try:
                # Restaura se minimizada
                if win32gui.IsIconic(self.hwnd):
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)

                # Foca
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.3)
                return True
            except Exception as e:
                print(f"   ⚠ Erro ao focar: {e}")
                return False
        return False

    def write_string(self, address: int, text: str, length: int = 32) -> bool:
        """Escreve string na memória"""
        try:
            # Trunca se necessário
            if len(text) > length - 1:
                text = text[:length - 1]

            # Converte para bytes com null terminator
            text_bytes = text.encode('latin-1') + b'\x00'

            # Padding
            padding = length - len(text_bytes)
            if padding > 0:
                text_bytes += b'\x00' * padding

            # Escreve
            self.pm.write_bytes(address, text_bytes, length)
            return True

        except Exception as e:
            print(f"   ✗ Erro: {e}")
            return False

    def read_string(self, address: int, length: int = 32) -> str:
        """Lê string da memória"""
        try:
            data = self.pm.read_bytes(address, length)
            null_pos = data.find(b'\x00')
            if null_pos != -1:
                data = data[:null_pos]
            return data.decode('latin-1', errors='ignore')
        except:
            return ""

    def write_and_validate(self, address: int, text: str, name: str) -> bool:
        """Escreve e valida"""
        # Escreve
        if not self.write_string(address, text, 32):
            return False

        time.sleep(0.1)

        # Lê de volta
        read_back = self.read_string(address, 32)

        # Valida
        if read_back == text:
            print(f"   ✓ {name}: '{text}' ✓")
            return True
        else:
            print(f"   ✗ {name} FALHOU!")
            print(f"      Esperado: '{text}'")
            print(f"      Obtido:   '{read_back}'")
            return False

    def write_credentials(self) -> bool:
        """Escreve credenciais na memória"""
        print("\n📝 ESCREVENDO NA MEMÓRIA")
        print("-"*70)

        print(f"\n   Endereços TibiaAPI:")
        print(f"   • Account:  0x{self.LOGIN_ACCOUNT:08X}")
        print(f"   • Password: 0x{self.LOGIN_PASSWORD:08X}")

        # Account
        print(f"\n   ⌨  Escrevendo Account...")
        if not self.write_and_validate(self.LOGIN_ACCOUNT, self.account, "Account"):
            return False

        # Password
        print(f"\n   ⌨  Escrevendo Password...")
        if not self.write_and_validate(self.LOGIN_PASSWORD, self.password, "Password"):
            return False

        print(f"\n   ✅ CREDENCIAIS ESCRITAS!")
        return True

    def is_in_game(self) -> bool:
        """Verifica se está no jogo"""
        try:
            player_id = self.pm.read_int(self.PLAYER_ID)
            player_hp = self.pm.read_int(self.PLAYER_HEALTH)
            return player_id > 0 and player_hp > 0
        except:
            return False

    def get_player_info(self) -> dict:
        """Lê info do player"""
        try:
            return {
                'id': self.pm.read_int(self.PLAYER_ID),
                'name': self.read_string(self.PLAYER_NAME, 32),
                'level': self.pm.read_int(self.PLAYER_LEVEL),
                'hp': self.pm.read_int(self.PLAYER_HEALTH),
                'max_hp': self.pm.read_int(self.PLAYER_MAX_HEALTH),
                'mana': self.pm.read_int(self.PLAYER_MANA),
                'max_mana': self.pm.read_int(self.PLAYER_MAX_MANA)
            }
        except:
            return {}

    def wait_for_game(self, timeout: int = 15) -> bool:
        """Aguarda entrar no jogo"""
        print(f"\n⏳ Aguardando entrada ({timeout}s)...")

        start = time.time()
        while time.time() - start < timeout:
            if self.is_in_game():
                info = self.get_player_info()
                print(f"\n✅ PLAYER LOGADO!")
                print(f"   Nome: {info.get('name', 'N/A')}")
                print(f"   Level: {info.get('level', 0)}")
                print(f"   HP: {info.get('hp', 0)}/{info.get('max_hp', 0)}")
                print(f"   Mana: {info.get('mana', 0)}/{info.get('max_mana', 0)}")
                return True

            remaining = int(timeout - (time.time() - start))
            print(f"\r   └─ {remaining}s   ", end='', flush=True)
            time.sleep(0.5)

        print(f"\n✗ Timeout")
        return False

    def run(self) -> bool:
        """Login automático"""
        print("\n" + "="*70)
        print("🤖 TIBIA 8.60 - LOGIN AUTOMÁTICO")
        print("="*70)
        print(f"Account: {self.account}")
        print(f"Password: {'*' * len(self.password)}")
        print(f"Char: {self.char_index}")
        print("="*70)

        try:
            # [1] Conectar
            print("\n[1/6] CONECTANDO")
            print("-"*70)
            if not self.connect():
                return False

            # [2] IMPORTANTE: Focar cliente
            print("\n[2/6] FOCANDO CLIENTE")
            print("-"*70)

            print("\n⚠️  IMPORTANTE: O cliente precisa estar em FOCO!")
            print("   Você tem 3 segundos para clicar na janela do jogo.")

            # Tenta focar automaticamente
            if self.focus_window_auto():
                print("   ✓ Janela focada automaticamente")
            else:
                print("   ⚠ Foco automático falhou")
                print("   👉 CLIQUE NA JANELA DO JOGO AGORA!")

            # Countdown
            for i in range(3, 0, -1):
                print(f"   └─ {i}...", end='\r', flush=True)
                time.sleep(1)

            print("   ✓ Continuando...                ")

            # [3] Escrever credenciais
            print("\n[3/6] ESCREVENDO CREDENCIAIS")
            print("-"*70)

            if not self.write_credentials():
                print("\n❌ FALHA ao escrever")
                return False

            # [4] Login
            print("\n[4/6] FAZENDO LOGIN")
            print("-"*70)

            print("   ↵ ENTER...")
            pyautogui.press('enter')
            time.sleep(3)
            print("   ✓ Aguardou lista de chars")

            # [5] Selecionar char
            print("\n[5/6] SELECIONANDO CHAR")
            print("-"*70)

            print("   ⬆ Topo...")
            for _ in range(10):
                pyautogui.press('up')
                time.sleep(0.05)

            time.sleep(0.3)

            if self.char_index > 0:
                print(f"   ⬇ Descendo {self.char_index}x...")
                for _ in range(self.char_index):
                    pyautogui.press('down')
                    time.sleep(0.1)

            print("   ✓ Char selecionado")

            print("\n   ↵ ENTER para entrar...")
            pyautogui.press('enter')
            time.sleep(0.5)

            # [6] Validar
            print("\n[6/6] VALIDANDO")
            print("-"*70)

            if not self.wait_for_game(timeout=15):
                return False

            print("\n" + "="*70)
            print("✅ LOGIN COMPLETO!")
            print("="*70)

            return True

        except KeyboardInterrupt:
            print("\n⚠ Interrompido")
            return False
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    ACCOUNT_NAME = "aaaa"
    PASSWORD = "aaa"
    CHARACTER_INDEX = 0

    if ACCOUNT_NAME == "seu_account":
        print("\n⚠️ CONFIGURE CREDENCIAIS!")
        return

    print("\n" + "="*70)
    print("📋 CHECKLIST PRÉ-EXECUÇÃO")
    print("="*70)
    print("   ✅ Kaldrox/Tibia 8.60 ABERTO")
    print("   ✅ Na tela de LOGIN (campos vazios)")
    print("   ✅ Execute como Administrador")
    print("   ⚠️  PREPARE-SE para clicar no jogo quando pedir!")
    print("="*70)

    input("\nPressione ENTER para iniciar...")

    bot = TibiaLogin860Final(
        account=ACCOUNT_NAME,
        password=PASSWORD,
        char_index=CHARACTER_INDEX
    )

    success = bot.run()

    if not success:
        print("\n" + "="*70)
        print("❌ LOGIN FALHOU")
        print("="*70)
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Você clicou na janela do jogo?")
        print("   2. O cliente estava na tela de login?")
        print("   3. Executou como Administrador?")
        print("   4. Credenciais corretas?")
        print("="*70)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         TIBIA 8.60 - LOGIN AUTOMÁTICO (Foco Manual)                  ║
║         Endereços oficiais TibiaAPI                                  ║
║         Você terá 3 segundos para focar o cliente!                   ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Encerrado")