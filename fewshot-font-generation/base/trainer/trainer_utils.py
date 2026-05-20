import torch
import torch.nn as nn
import numpy as np
from scipy.optimize import linear_sum_assignment

def load_checkpoint(path, gen, disc, aux_clf, g_optim, d_optim, ac_optim, force_resume=False):
    if not path:
        return 0

    print(f"Loading checkpoint from {path} ...")
    
    try:
        # PyTorch 2.6+ 보안 에러 회피 (weights_only=False)
        ckpt = torch.load(path, map_location='cpu', weights_only=False)
    except TypeError:
        # 구버전 PyTorch 호환
        ckpt = torch.load(path, map_location='cpu')
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return 0

    if 'generator' in ckpt:
        gen.load_state_dict(ckpt['generator'])
        if disc is not None and 'discriminator' in ckpt:
            disc.load_state_dict(ckpt['discriminator'])
        if aux_clf is not None and 'aux_clf' in ckpt:
            aux_clf.load_state_dict(ckpt['aux_clf'])
        if g_optim is not None and 'g_optim' in ckpt:
            g_optim.load_state_dict(ckpt['g_optim'])
        if d_optim is not None and 'd_optim' in ckpt:
            d_optim.load_state_dict(ckpt['d_optim'])
        if ac_optim is not None and 'ac_optim' in ckpt:
            ac_optim.load_state_dict(ckpt['ac_optim'])
        step = ckpt.get('step', 0)
    else:
        print("Warning: 'generator' key not found. Loading weights directly.")
        gen.load_state_dict(ckpt, strict=False)
        step = 0
        
    return step

def has_bn(model):
    for m in model.modules():
        if isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)):
            return True
    return False

def freeze_params(params):
    for p in params:
        p.requires_grad = False

def param_count(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def overwrite_weight(dst_dict, src_dict):
    for k, v in src_dict.items():
        if k in dst_dict:
            dst_dict[k] = v

def cyclize(loader):
    while True:
        for x in loader:
            yield x

def binarize_labels(labels, n_tags):
    # 리스트 입력 처리 강화 (Jagged List 지원)
    if isinstance(labels, list):
        if len(labels) > 0 and isinstance(labels[0], list):
            batch_size = len(labels)
            out = torch.zeros(batch_size, n_tags)
            for i, row in enumerate(labels):
                for tag in row:
                    if 0 <= tag < n_tags:
                        out[i, tag] = 1
            return out
        else:
            try:
                labels = torch.tensor(labels)
            except ValueError:
                return torch.zeros(len(labels), n_tags)
    
    if isinstance(labels, torch.Tensor):
        if labels.ndim == 1:
            return torch.zeros(labels.size(0), n_tags).to(labels.device).scatter_(1, labels.view(-1, 1).long(), 1)
            
    return labels

def expert_assign(input_data, n_experts=None, n_tags=None):
    """
    상황에 따라 두 가지 모드로 동작하는 하이브리드 함수
    1. 인자가 3개일 때: 정적 할당 (기존 방식)
    2. 인자가 1개일 때: 헝가리안 매칭 (Hungarian Algorithm) - MX-Font 방식
    """
    
    # Case 1: 정적 할당 (Static Assignment)
    if n_experts is not None and n_tags is not None:
        labels = input_data
        if isinstance(labels, list):
            try:
                labels = torch.tensor(labels)
            except:
                pass
        return labels // (n_tags // n_experts)

    # Case 2: 동적 할당 (Hungarian Matching)
    # input_data는 여기서 'T_probs' (확률 행렬) 입니다.
    else:
        probs = input_data
        # 텐서라면 numpy로 변환 (scipy 사용을 위해)
        if isinstance(probs, torch.Tensor):
            cost_matrix = probs.detach().cpu().numpy()
        else:
            cost_matrix = probs
            
        # linear_sum_assignment는 비용을 '최소화' 하려 하므로,
        # 확률을 '최대화' 하기 위해 음수(-)를 붙여줍니다.
        row_ind, col_ind = linear_sum_assignment(-cost_matrix)
        
        # 결과를 다시 텐서로 변환하여 반환
        return torch.from_numpy(row_ind), torch.from_numpy(col_ind)
