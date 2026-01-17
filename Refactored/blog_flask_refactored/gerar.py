import os
import ast
from radon.complexity import cc_visit, cc_rank
from radon.metrics import mi_visit
from colorama import init, Fore, Style

init(autoreset=True)

def analyze_file_complexity(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    try:
        blocks = cc_visit(content)
        total_cc = sum(block.complexity for block in blocks)
        max_cc = max([block.complexity for block in blocks]) if blocks else 0
    except:
        return None

    try:
        mi = mi_visit(content, multi=False)
    except:
        mi = 100

    try:
        tree = ast.parse(content)
        imports = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1
    except:
        imports = 0

    return {
        'total_cc': total_cc,
        'max_cc': max_cc,
        'mi': mi,
        'imports': imports
    }

def main():
    print(f"{'ARQUIVO':<40} | {'TOTAL CC':<10} | {'PIOR FUNC':<13} | {'IMPORTS':<8} | {'MI (Manut.)':<10}")
    print("-" * 95)
    
    data = []
    search_path = "app" 
    
    if not os.path.exists(search_path):
        print(f"Erro: Pasta '{search_path}' não encontrada. Rode o script na raiz do projeto.")
        return

    for root, dirs, files in os.walk(search_path):
        if "venv" in root or "__pycache__" in root: continue
        
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                
                rel_path = os.path.relpath(full_path, start=os.getcwd())
                if rel_path.startswith("app" + os.sep):
                    rel_path = rel_path[4:]
                
                metrics = analyze_file_complexity(full_path)
                
                if metrics and metrics['total_cc'] > 0:
                    rank = cc_rank(metrics['max_cc'])
                    
                    color = Fore.GREEN
                    if rank == 'C': color = Fore.YELLOW
                    if rank in ['D', 'E', 'F']: color = Fore.RED
                    
                    rank_display = f"{color}{metrics['max_cc']} ({rank}){Style.RESET_ALL}"
                    
                    print(f"{rel_path:<40} | {metrics['total_cc']:<10} | {rank_display:<22} | {metrics['imports']:<8} | {metrics['mi']:.1f}")
                    data.append(metrics)

    print("-" * 95)

if __name__ == "__main__":
    main()