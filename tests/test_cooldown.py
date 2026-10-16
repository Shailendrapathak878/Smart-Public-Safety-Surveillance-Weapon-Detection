import pytest
import time
from alerts.cooldown import CooldownManager

def test_cooldown_manager():
    manager = CooldownManager()
    manager.cooldown_seconds = 0.5 # Fast for testing
    
    # First trigger should always pass
    assert manager.can_trigger() == True
    
    # Second trigger immediately should fail
    assert manager.can_trigger() == False
    
    # Wait for cooldown
    time.sleep(0.6)
    
    # Third trigger should pass
    assert manager.can_trigger() == True
