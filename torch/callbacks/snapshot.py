from .base import CallbackTemplate
import torch
from torch.nn.parallel import DataParallel, DistributedDataParallel


def _save_snapshot(trainer, path):
    if isinstance(
            trainer.model,
            (DataParallel, DistributedDataParallel)):
        module = trainer.model.module
    else:
        module = trainer.model
    
    serialized = {
        'global_epoch': trainer.global_epoch,
        'model': module.state_dict(),
        'optimizer': trainer.optimizer.state_dict(),
        'scheduler': trainer.scheduler.state_dict(),
        'state': trainer.state,
        'all_states': trainer._states
    }

    if trainer.xla:
        import torch_xla.utils.serialization as xser
        xser.save(serialized, str(path))
    else:
        torch.save(serialized, str(path))


def _load_snapshot(trainer, path, device):
    if trainer.xla:
        import torch_xla.utils.serialization as xser
        checkpoint = xser.load(str(path))
    else:
        checkpoint = torch.load(str(path), map_location=device)

    if isinstance(
            trainer.model,
            (DataParallel, DistributedDataParallel)):
        trainer.model.module.load_state_dict(checkpoint['model'])
    else:
        trainer.model.load_state_dict(checkpoint['model'])

    if hasattr(trainer, 'optimizer'):
        trainer.optimizer.load_state_dict(checkpoint['optimizer'])
    if hasattr(trainer, 'scheduler'):
        trainer.scheduler.load_state_dict(checkpoint['scheduler'])
    if hasattr(trainer, 'global_epoch'):
        trainer.global_epoch = checkpoint['global_epoch']
    trainer.state = checkpoint['state']
    trainer._states = checkpoint['all_states']


class SaveAllSnapshots(CallbackTemplate):
    def __init__(self, path=None):
        super().__init__()

    def save_snapshot(self, trainer, path):
        if path is None:
            path = trainer.base_dir / f'{trainer.serial}_epoch_{trainer.global_epoch}.pt'
        
        _save_snapshot(trainer, path)

    def load_snapshot(self, trainer, path=None, device=None):
        if path is None:
            if trainer.state['best_epoch'] is None:
                # Pickup best
                path = trainer.base_dir / f'{trainer.serial}_epoch_{trainer.state["best_epoch"]}.pt'
            else:
                # Pickup latest
                path = sorted(list(trainer.base_dir.glob(f'{trainer.serial}_epoch_*.pt')))[-1]

        if device is None:
            device = trainer.device
        
        _load_snapshot(trainer, path, device)
        print(trainer.state)
        

class SaveSnapshot(CallbackTemplate):
    '''
    Path priority: path argument > BestEpoch.path > trainer.snapshot_path
    '''

    def __init__(self, path=None):
        super().__init__()
        self.path = path

    def save_snapshot(self, trainer, path):
        if path is None:
            path = self.path if self.path is not None else trainer.snapshot_path
        _save_snapshot(trainer, path)

    def load_snapshot(self, trainer, path=None, device=None):
        if path is None:
            path = self.path if self.path is not None else trainer.snapshot_path
        if device is None:
            device = trainer.device
        _load_snapshot(trainer, path, device)
