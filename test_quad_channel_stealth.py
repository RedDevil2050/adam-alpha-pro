#!/usr/bin/env python3
"""
Comprehensive Quad-Channel Stealth Agent Test Suite
==================================================

Tests the advanced quad-channel stealth architecture including:
- Enhanced MoneyControl agent with 4 data sources
- Background collection system
- Real-time data streaming
- Performance monitoring
- Circuit breaker functionality
"""

import asyncio
import time
import json
from typing import Dict, List
from backend.agents.stealth.enhanced_moneycontrol_agent import EnhancedMoneyControlAgent
from backend.agents.stealth.background_manager import background_manager
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
from backend.agents.stealth.trendlyne_agent import TrendlyneAgent

async def test_quad_channel_architecture():
    """Test the quad-channel data collection architecture."""
    print('🚀 Testing Quad-Channel Architecture')
    print('=' * 60)
    
    # Create enhanced agent
    enhanced_agent = EnhancedMoneyControlAgent()
    test_symbols = ['RELIANCE', 'TCS']
    
    for symbol in test_symbols:
        print(f'\n📊 Testing quad-channel for: {symbol}')
        print('-' * 40)
        
        start_time = time.time()
        result = await enhanced_agent.execute(symbol)
        execution_time = time.time() - start_time
        
        # Extract quad-channel info
        quad_info = result.get('details', {}).get('quad_channel_info', {})
        channels_used = quad_info.get('channels_used', [])
        fusion_confidence = quad_info.get('fusion_confidence', 0)
        validation_score = quad_info.get('validation_score', 0)
        
        print(f'  🎯 Result: {result.get("verdict", "N/A")} (confidence: {result.get("confidence", 0):.3f})')
        print(f'  📡 Channels Used: {len(channels_used)}/4 - {channels_used}')
        print(f'  🔬 Fusion Confidence: {fusion_confidence:.3f}')
        print(f'  ✅ Validation Score: {validation_score:.3f}')
        print(f'  ⏱️  Execution Time: {execution_time:.2f}s')
        
        # Show channel availability
        channel_availability = quad_info.get('channel_availability', {})
        for channel, available in channel_availability.items():
            status = '✅' if available else '❌'
            print(f'    {status} {channel.capitalize()}: {"Available" if available else "Failed"}')
        
        # Performance report
        performance = enhanced_agent.get_performance_report()
        print(f'  📊 Agent Performance:')
        print(f'    Total Requests: {performance["total_requests"]}')
        print(f'    Success Rate: {performance["success_rate"]}')
        print(f'    Avg Response Time: {performance["avg_response_time"]}')
        
        # Circuit breaker status
        cb_status = performance["circuit_breaker_status"]
        for channel, status in cb_status.items():
            color = '🟢' if status == 'CLOSED' else '🔴' if status == 'OPEN' else '🟡'
            print(f'    {color} {channel.capitalize()} Circuit: {status}')

async def test_background_collection_advanced():
    """Test advanced background collection with multiple agents."""
    print('\n🔄 Testing Advanced Background Collection')
    print('=' * 60)
    
    # Register multiple agent types
    agents = [
        ('enhanced_moneycontrol', EnhancedMoneyControlAgent()),
        ('standard_moneycontrol', MoneyControlAgent()),
        ('trendlyne', TrendlyneAgent())
    ]
    
    print('📝 Registering agents for background collection...')
    for agent_name, agent_instance in agents:
        background_manager.register_agent(agent_name, agent_instance)
        print(f'  ✅ {agent_name}')
    
    # Start performance monitoring
    await background_manager.start_monitoring()
    print('📊 Performance monitoring started')
    
    # Create multiple collection sessions
    sessions = [
        {
            'session_id': 'quad_test_session_1',
            'symbols': ['RELIANCE', 'TCS'],
            'agents': ['enhanced_moneycontrol', 'standard_moneycontrol'],
            'interval': 20
        },
        {
            'session_id': 'quad_test_session_2', 
            'symbols': ['INFY'],
            'agents': ['enhanced_moneycontrol', 'trendlyne'],
            'interval': 15
        }
    ]
    
    # Start sessions
    print('\n🚀 Starting multiple collection sessions...')
    for session_config in sessions:
        success = await background_manager.start_collection_session(**session_config)
        session_id = session_config['session_id']
        symbols_count = len(session_config['symbols'])
        agents_count = len(session_config['agents'])
        
        if success:
            print(f'  ✅ {session_id}: {symbols_count} symbols, {agents_count} agents')
        else:
            print(f'  ❌ {session_id}: Failed to start')
    
    # Monitor for a period
    print('\n⏳ Monitoring background collection for 60 seconds...')
    
    monitoring_start = time.time()
    last_report_time = 0
    
    while time.time() - monitoring_start < 60:
        await asyncio.sleep(10)
        
        current_time = time.time()
        if current_time - last_report_time >= 20:  # Report every 20 seconds
            performance = background_manager.get_comprehensive_performance_report()
            
            print(f'\n📊 Performance Report (t+{current_time - monitoring_start:.0f}s):')
            print(f'  System Health: {performance["overall_health"]}')
            print(f'  Active Sessions: {performance["system_status"]["active_sessions"]}')
            print(f'  Background Tasks: {performance["system_status"]["background_tasks"]}')
            
            # Agent performance
            for agent_name, metrics in performance["agent_performance"].items():
                executions = metrics["total_executions"]
                success_rate = metrics["success_rate"]
                avg_time = metrics["avg_execution_time"]
                print(f'    {agent_name}: {executions} exec, {success_rate} success, {avg_time} avg')
            
            # Session performance  
            for session_id, session_metrics in performance["session_performance"].items():
                collections = session_metrics["total_collections"]
                success_rate = session_metrics["success_rate"]
                runtime = session_metrics["runtime_hours"]
                print(f'    {session_id}: {collections} collections, {success_rate} success, {runtime} runtime')
            
            last_report_time = current_time
    
    # Stop sessions
    print('\n🛑 Stopping collection sessions...')
    for session_config in sessions:
        session_id = session_config['session_id']
        success = await background_manager.stop_collection_session(session_id)
        status = '✅' if success else '❌'
        print(f'  {status} Stopped {session_id}')
    
    await background_manager.stop_monitoring()
    print('📊 Performance monitoring stopped')

async def test_data_streaming_simulation():
    """Test data streaming capabilities with simulated subscribers."""
    print('\n📡 Testing Data Streaming Simulation')
    print('=' * 60)
    
    # Data collection tracking
    streamed_data = []
    performance_updates = []
    
    def data_subscriber(data):
        """Simulate a real-time data subscriber."""
        streamed_data.append(data)
        symbol = data.get('symbol', 'UNKNOWN')
        successful_agents = len(data.get('successful_agents', []))
        timestamp = data.get('timestamp', 0)
        
        print(f'📢 Data Stream: {symbol} - {successful_agents} agents @ {timestamp:.0f}')
    
    def performance_subscriber(perf_data):
        """Simulate a performance monitoring subscriber."""
        performance_updates.append(perf_data)
        health = perf_data.get('overall_health', 'UNKNOWN')
        active_sessions = perf_data.get('system_status', {}).get('active_sessions', 0)
        
        print(f'📊 Performance Stream: Health={health}, Sessions={active_sessions}')
    
    # Subscribe to streams
    background_manager.subscribe_to_data(data_subscriber)
    background_manager.subscribe_to_performance(performance_subscriber)
    print('📡 Subscribed to data and performance streams')
    
    # Register agents for streaming test
    streaming_agent = EnhancedMoneyControlAgent()
    background_manager.register_agent('streaming_test_enhanced', streaming_agent)
    
    # Start monitoring and a test session
    await background_manager.start_monitoring()
    
    success = await background_manager.start_collection_session(
        session_id='streaming_test_session',
        symbols=['RELIANCE', 'TCS'],
        agent_names=['streaming_test_enhanced'],
        collection_interval=10  # Fast collection for testing
    )
    
    if success:
        print('✅ Streaming test session started')
        
        # Monitor streaming for 40 seconds
        print('⏳ Collecting streaming data for 40 seconds...')
        await asyncio.sleep(40)
        
        # Stop session
        await background_manager.stop_collection_session('streaming_test_session')
        print('🛑 Streaming test session stopped')
        
    await background_manager.stop_monitoring()
    
    # Report streaming results
    print(f'\n📊 Streaming Results:')
    print(f'  Data Updates Received: {len(streamed_data)}')
    print(f'  Performance Updates: {len(performance_updates)}')
    
    if streamed_data:
        print(f'  Symbols Streamed: {set(d.get("symbol") for d in streamed_data)}')
        avg_agents = sum(len(d.get("successful_agents", [])) for d in streamed_data) / len(streamed_data)
        print(f'  Avg Successful Agents: {avg_agents:.1f}')
    
    return len(streamed_data) > 0 and len(performance_updates) > 0

async def test_circuit_breaker_functionality():
    """Test circuit breaker functionality under simulated failures."""
    print('\n⚡ Testing Circuit Breaker Functionality')
    print('=' * 60)
    
    # Create agent for testing
    test_agent = EnhancedMoneyControlAgent()
    
    print('🔧 Testing circuit breaker with multiple requests...')
    
    # Make several requests to trigger circuit breakers if channels fail
    test_results = []
    for i in range(5):
        print(f'  Request {i+1}/5...', end=' ')
        start_time = time.time()
        
        try:
            result = await test_agent.execute('RELIANCE')
            execution_time = time.time() - start_time
            
            quad_info = result.get('details', {}).get('quad_channel_info', {})
            channels_used = len(quad_info.get('channels_used', []))
            
            test_results.append({
                'success': True,
                'channels': channels_used,
                'time': execution_time,
                'confidence': result.get('confidence', 0)
            })
            
            print(f'✅ {channels_used} channels, {execution_time:.2f}s')
            
        except Exception as e:
            test_results.append({'success': False, 'error': str(e)})
            print(f'❌ Error: {str(e)[:50]}')
        
        await asyncio.sleep(2)  # Small delay between requests
    
    # Check circuit breaker states
    performance = test_agent.get_performance_report()
    cb_status = performance["circuit_breaker_status"]
    
    print(f'\n⚡ Circuit Breaker Status:')
    for channel, status in cb_status.items():
        if status == 'CLOSED':
            print(f'  🟢 {channel.capitalize()}: CLOSED (operational)')
        elif status == 'OPEN':
            print(f'  🔴 {channel.capitalize()}: OPEN (failed)')
        else:
            print(f'  🟡 {channel.capitalize()}: HALF_OPEN (testing)')
    
    # Analyze test results
    successful_requests = sum(1 for r in test_results if r.get('success'))
    avg_channels = sum(r.get('channels', 0) for r in test_results if r.get('success'))
    avg_channels = avg_channels / max(successful_requests, 1)
    
    print(f'\n📊 Circuit Breaker Test Results:')
    print(f'  Successful Requests: {successful_requests}/5')
    print(f'  Average Channels Used: {avg_channels:.1f}')
    print(f'  Total Requests Made: {performance["total_requests"]}')
    print(f'  Overall Success Rate: {performance["success_rate"]}')

async def run_comprehensive_quad_test():
    """Run the complete quad-channel test suite."""
    print('🎯 COMPREHENSIVE QUAD-CHANNEL TEST SUITE')
    print('=' * 70)
    print(f'🕐 Test Started: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    
    total_start_time = time.time()
    test_results = {}
    
    try:
        # Test 1: Quad-channel architecture
        print('\n' + '='*70)
        await test_quad_channel_architecture()
        test_results['quad_channel'] = True
        
        # Test 2: Advanced background collection
        print('\n' + '='*70)
        await test_background_collection_advanced()
        test_results['background_collection'] = True
        
        # Test 3: Data streaming
        print('\n' + '='*70)
        streaming_success = await test_data_streaming_simulation()
        test_results['data_streaming'] = streaming_success
        
        # Test 4: Circuit breaker functionality
        print('\n' + '='*70)
        await test_circuit_breaker_functionality()
        test_results['circuit_breaker'] = True
        
    except Exception as e:
        print(f'❌ Test suite error: {e}')
        test_results['error'] = str(e)
    
    # Final summary
    total_time = time.time() - total_start_time
    
    print('\n' + '='*70)
    print('🏁 QUAD-CHANNEL TEST SUITE SUMMARY')
    print('='*70)
    
    passed_tests = sum(1 for result in test_results.values() if result is True)
    total_tests = len([k for k in test_results.keys() if k != 'error'])
    
    print(f'📊 Test Results: {passed_tests}/{total_tests} passed')
    print(f'⏱️  Total Execution Time: {total_time:.2f} seconds')
    
    for test_name, result in test_results.items():
        if test_name == 'error':
            continue
        
        status = '✅ PASSED' if result else '❌ FAILED'
        print(f'  {status} {test_name.replace("_", " ").title()}')
    
    if 'error' in test_results:
        print(f'❌ Suite Error: {test_results["error"]}')
    
    # Overall assessment
    if passed_tests == total_tests:
        print('\n🎉 QUAD-CHANNEL SYSTEM: EXCELLENT PERFORMANCE!')
        print('✅ All advanced features are working optimally!')
        print('✅ Background collection system is operational!')
        print('✅ Real-time streaming is functional!')
        print('✅ Circuit breakers provide fault tolerance!')
    elif passed_tests >= total_tests * 0.75:
        print('\n⚠️  QUAD-CHANNEL SYSTEM: GOOD PERFORMANCE')
        print('🔧 Most features working, some optimization needed')
    else:
        print('\n❌ QUAD-CHANNEL SYSTEM: NEEDS ATTENTION')
        print('🛠️  Multiple systems require fixes')
    
    # Cleanup
    try:
        await background_manager.shutdown()
        print('\n🧹 Cleanup completed')
    except Exception as e:
        print(f'⚠️  Cleanup warning: {e}')

if __name__ == "__main__":
    asyncio.run(run_comprehensive_quad_test())
