#!/usr/bin/env python3
"""
Integration Test Suite for Enhanced Web Agent Components
Validates the reliability and performance of production-grade components.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from example.enhanced_integration import (
    RateLimitManager, ContentOptimizer, ErrorRecovery, 
    PerformanceTracker, AGIEnhancedAgent
)

class TestRateLimitManager:
    """Test rate limiting functionality."""
    
    def test_initialization(self):
        manager = RateLimitManager()
        assert manager.config.tpm_limit == 150000
        assert manager.config.rpm_limit == 10000
        assert manager.config.token_buffer == 5000
        
    def test_token_estimation(self):
        manager = RateLimitManager()
        text = "Hello world" * 100
        tokens = manager.estimate_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
        
    def test_rate_limit_check(self):
        manager = RateLimitManager()
        # Should pass initially
        assert manager.check_rate_limits(1000) == True
        
        # Simulate high usage
        manager.current_tpm = 149000
        manager.current_rpm = 9900
        assert manager.check_rate_limits(2000) == False
        
    def test_usage_update(self):
        manager = RateLimitManager()
        initial_tpm = manager.current_tpm
        manager.update_usage(1000)
        assert manager.current_tpm == initial_tpm + 1000

class TestContentOptimizer:
    """Test content optimization strategies."""
    
    def test_initialization(self):
        optimizer = ContentOptimizer()
        assert optimizer.max_tokens == 4000
        assert optimizer.truncation_strategy == "smart"
        
    def test_basic_truncation(self):
        optimizer = ContentOptimizer(truncation_strategy="basic")
        long_text = "word " * 1000
        result = optimizer.optimize_content(long_text, max_tokens=100)
        assert len(result) < len(long_text)
        
    def test_smart_truncation_omnizon(self):
        optimizer = ContentOptimizer(truncation_strategy="smart")
        content = "Product: iPhone 15 Pro\nPrice: $999\nDescription: " + "detail " * 500
        result = optimizer.optimize_content(content, max_tokens=200, task_type="omnizon")
        assert "Product: iPhone 15 Pro" in result
        assert "Price: $999" in result
        
    def test_preserve_structure(self):
        optimizer = ContentOptimizer()
        structured_content = "# Header\n## Subheader\nContent here"
        result = optimizer.optimize_content(structured_content, max_tokens=50)
        assert "# Header" in result or "Header" in result

class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_initialization(self):
        recovery = ErrorRecovery()
        assert recovery.max_retries == 3
        assert recovery.base_delay == 1.0
        assert recovery.max_delay == 60.0
        
    def test_should_retry_logic(self):
        recovery = ErrorRecovery()
        
        # Should retry on rate limit
        assert recovery.should_retry("Rate limit exceeded", attempt=1) == True
        
        # Should retry on timeout
        assert recovery.should_retry("Request timeout", attempt=2) == True
        
        # Should not retry on max attempts
        assert recovery.should_retry("Rate limit exceeded", attempt=4) == False
        
        # Should not retry on auth error
        assert recovery.should_retry("Authentication failed", attempt=1) == False
        
    def test_exponential_backoff(self):
        recovery = ErrorRecovery()
        delay1 = recovery.calculate_delay(1)
        delay2 = recovery.calculate_delay(2)
        delay3 = recovery.calculate_delay(3)
        
        assert delay1 < delay2 < delay3
        assert delay3 <= recovery.max_delay
        
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        recovery = ErrorRecovery(max_retries=2, base_delay=0.1)
        
        call_count = 0
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Rate limit exceeded")
            return "success"
            
        result = await recovery.retry_with_backoff(failing_function)
        assert result == "success"
        assert call_count == 2

class TestPerformanceTracker:
    """Test performance monitoring."""
    
    def test_initialization(self):
        tracker = PerformanceTracker()
        assert tracker.total_requests == 0
        assert tracker.successful_requests == 0
        assert tracker.failed_requests == 0
        
    def test_request_tracking(self):
        tracker = PerformanceTracker()
        
        # Track successful request
        tracker.track_request(success=True, duration=1.5, tokens_used=100)
        assert tracker.total_requests == 1
        assert tracker.successful_requests == 1
        assert tracker.failed_requests == 0
        
        # Track failed request
        tracker.track_request(success=False, duration=0.5, tokens_used=50)
        assert tracker.total_requests == 2
        assert tracker.successful_requests == 1
        assert tracker.failed_requests == 1
        
    def test_metrics_calculation(self):
        tracker = PerformanceTracker()
        
        # Add some test data
        tracker.track_request(True, 1.0, 100)
        tracker.track_request(True, 2.0, 200)
        tracker.track_request(False, 0.5, 50)
        
        metrics = tracker.get_metrics()
        assert abs(metrics['success_rate'] - 2/3) < 0.01
        assert abs(metrics['avg_duration'] - 1.17) < 0.01  # (1.0 + 2.0 + 0.5) / 3
        assert metrics['total_tokens'] == 350
        
    def test_performance_optimization_suggestions(self):
        tracker = PerformanceTracker()
        
        # Simulate poor performance
        for _ in range(10):
            tracker.track_request(False, 5.0, 1000)
            
        metrics = tracker.get_metrics()
        assert metrics['success_rate'] < 0.5
        assert metrics['avg_duration'] > 3.0

class TestAGIEnhancedAgent:
    """Test the main enhanced agent integration."""
    
    def test_initialization(self):
        agent = AGIEnhancedAgent()
        assert agent.rate_limiter is not None
        assert agent.content_optimizer is not None
        assert agent.error_recovery is not None
        assert agent.performance_tracker is not None
        
    @patch('example.enhanced_integration.AGIEnhancedAgent._execute_base_agent')
    def test_enhanced_execution_success(self, mock_execute):
        agent = AGIEnhancedAgent()
        mock_execute.return_value = "test result"
        
        result = agent.execute_task("test task", max_tokens=1000)
        
        assert result["success"] == True
        assert result["result"] == "test result"
        assert agent.performance_tracker.total_requests == 1
        assert agent.performance_tracker.successful_requests == 1
        
    @patch('example.enhanced_integration.AGIEnhancedAgent._execute_base_agent')
    def test_enhanced_execution_with_retry(self, mock_execute):
        agent = AGIEnhancedAgent()
        
        # First call fails, second succeeds
        mock_execute.side_effect = [
            Exception("Rate limit exceeded"),
            "retry success"
        ]
        
        result = agent.execute_task("test task", max_tokens=1000)
        
        assert result["success"] == True
        assert result["result"] == "retry success"
        assert mock_execute.call_count == 2
        
    def test_content_optimization_integration(self):
        agent = AGIEnhancedAgent()
        
        long_content = "word " * 2000
        optimized = agent.content_optimizer.optimize_content(long_content, max_tokens=100)
        
        assert len(optimized) < len(long_content)
        
    def test_rate_limiting_integration(self):
        agent = AGIEnhancedAgent()
        
        # Should pass with reasonable token count
        assert agent.rate_limiter.check_rate_limits(1000) == True
        
        # Should fail with excessive token count
        agent.rate_limiter.current_tpm = 149000
        assert agent.rate_limiter.check_rate_limits(2000) == False

class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    def test_omnizon_task_optimization(self):
        """Test optimization for Omnizon e-commerce tasks."""
        agent = AGIEnhancedAgent()
        
        # Simulate Omnizon product page content
        product_content = (
            "Product: MacBook Pro 16-inch\n"
            "Price: $2,399.00\n"
            "Rating: 4.8/5 stars\n"
            "Description: " + "Amazing laptop with great performance. " * 100
        )
        
        optimized = agent.content_optimizer.optimize_content(
            product_content, 
            max_tokens=200, 
            task_type="omnizon"
        )
        
        # Should preserve key product information
        assert "MacBook Pro 16-inch" in optimized
        assert "$2,399.00" in optimized
        assert "4.8/5" in optimized
        
    def test_staynb_task_optimization(self):
        """Test optimization for StayNB booking tasks."""
        agent = AGIEnhancedAgent()
        
        booking_content = (
            "Hotel: Grand Plaza\n"
            "Location: New York City\n"
            "Price: $299/night\n"
            "Amenities: " + "Pool, Gym, WiFi, Breakfast. " * 50
        )
        
        optimized = agent.content_optimizer.optimize_content(
            booking_content,
            max_tokens=150,
            task_type="staynb"
        )
        
        # Should preserve key booking information
        assert "Grand Plaza" in optimized
        assert "New York City" in optimized
        assert "$299/night" in optimized
        
    def test_end_to_end_reliability(self):
        """Test end-to-end reliability with simulated failures."""
        agent = AGIEnhancedAgent()
        
        # Track multiple task executions
        results = []
        for i in range(5):
            try:
                # Simulate varying task complexity
                task = f"test task {i}"
                result = agent.execute_task(task, max_tokens=500 + i * 100)
                results.append(result.get("success", False))
            except Exception as e:
                results.append(False)
                
        # Should maintain high reliability
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8  # 80% minimum success rate
        
    def test_performance_metrics_accuracy(self):
        """Test accuracy of performance metrics collection."""
        agent = AGIEnhancedAgent()
        
        # Simulate various request patterns
        agent.performance_tracker.track_request(True, 1.0, 100)
        agent.performance_tracker.track_request(True, 2.0, 200)
        agent.performance_tracker.track_request(False, 0.5, 50)
        agent.performance_tracker.track_request(True, 1.5, 150)
        
        metrics = agent.performance_tracker.get_metrics()
        
        assert metrics['total_requests'] == 4
        assert metrics['success_rate'] == 0.75  # 3/4
        assert abs(metrics['avg_duration'] - 1.25) < 0.01  # (1.0+2.0+0.5+1.5)/4
        assert metrics['total_tokens'] == 500

if __name__ == "__main__":
    # Run the test suite
    pytest.main(["-v", __file__])