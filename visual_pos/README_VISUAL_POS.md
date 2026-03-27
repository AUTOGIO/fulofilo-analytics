# FulôFiló — Visual POS (Sistema de Reconhecimento Visual)

## O que é?

O **Visual POS** usa **YOLOv11** (o modelo de detecção de objetos mais moderno da Ultralytics) para identificar produtos FulôFiló em tempo real através da câmera do iMac M3. Quando um produto é reconhecido, o sistema pode exibir automaticamente o preço, o SKU e o estoque disponível.

## Estrutura de Pastas

```
visual_pos/
├── images/
│   ├── train/     ← Fotos dos produtos para treinamento (você adiciona)
│   └── val/       ← Fotos para validação (você adiciona)
├── labels/
│   ├── train/     ← Arquivos .txt com anotações YOLO (gerados pelo Roboflow)
│   └── val/       ← Arquivos .txt com anotações YOLO (gerados pelo Roboflow)
├── runs/          ← Resultados do treinamento (gerado automaticamente)
├── dataset.yaml   ← Configuração do dataset (48 classes = 48 produtos)
├── train.py       ← Script de treinamento
└── predict.py     ← Script de inferência em tempo real
```

## Passo a Passo para Começar

### 1. Fotografar os Produtos

- Tire **10–20 fotos** de cada produto
- Varie os ângulos: frente, lado, 45°, com fundo diferente
- Resolução mínima: 640×640 pixels
- Salve em `visual_pos/images/train/` (80%) e `visual_pos/images/val/` (20%)

### 2. Anotar as Imagens (Labeling)

Use o **Roboflow** (gratuito para projetos privados pequenos):

1. Acesse [roboflow.com](https://roboflow.com) e crie uma conta
2. Crie um novo projeto: **Object Detection**
3. Faça upload das imagens de `images/train/`
4. Anote cada produto desenhando um bounding box e selecionando a classe
5. Exporte no formato **YOLOv8** (compatível com YOLOv11)
6. Copie os arquivos `.txt` para `visual_pos/labels/train/` e `labels/val/`

### 3. Treinar o Modelo

```bash
# Instalar dependências
uv add ultralytics

# Treinar (usa GPU MPS do M3 automaticamente)
uv run python visual_pos/train.py
```

O treinamento leva ~30 minutos no M3 com 500 imagens.

### 4. Testar em Tempo Real

```bash
# Webcam do iMac
uv run python visual_pos/predict.py --source 0

# Imagem específica
uv run python visual_pos/predict.py --source caminho/para/foto.jpg
```

## Dicas de Performance no M3

| Configuração | Valor Recomendado |
|---|---|
| Modelo | `yolo11n.pt` (nano) — mais rápido |
| Batch size | 16 |
| Image size | 640 |
| Device | `mps` (Apple Silicon GPU) |
| Epochs | 100 com early stopping |

## Integração com o Dashboard

Após o treinamento, o modelo pode ser integrado à página **Operações Diárias** do Streamlit para registro automático de vendas por câmera.
