import logging
import concurrent.futures
from typing import Callable, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """
    Gerenciador centralizado de tarefas em background.
    Usa um ThreadPoolExecutor compartilhado para evitar a criação manual de Threads.
    """
    _executor: concurrent.futures.ThreadPoolExecutor = None

    @classmethod
    def get_executor(cls) -> concurrent.futures.ThreadPoolExecutor:
        if cls._executor is None:
            # Configuração conservadora de workers por padrão
            cls._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=10,
                thread_name_prefix="bg-task-"
            )
            logger.info("Executador de tarefas em background inicializado (max_workers=10)")
        return cls._executor

    @classmethod
    def run_task(cls, func: Callable, *args, **kwargs) -> concurrent.futures.Future:
        """
        Enfileira uma função para execução assíncrona.
        """
        executor = cls.get_executor()
        logger.debug(f"Enfileirando tarefa: {func.__name__}")
        return executor.submit(func, *args, **kwargs)

    @classmethod
    def shutdown(cls):
        if cls._executor:
            logger.info("Encerrando executador de tarefas em background...")
            cls._executor.shutdown(wait=True)
            cls._executor = None

# Atalho para uso fácil
background_task_manager = BackgroundTaskManager()
