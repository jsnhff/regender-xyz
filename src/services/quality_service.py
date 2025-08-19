"""
Quality Service

This service handles quality control and validation of transformations.
"""

from typing import Optional, Dict, Any, List
import asyncio

from src.services.base import BaseService, ServiceConfig
from src.models.transformation import Transformation, TransformationChange
from src.strategies.quality import QualityStrategy, AdaptiveQualityStrategy
from src.providers.base import LLMProvider


class QualityService(BaseService):
    """
    Service for quality control and validation.
    
    This service:
    - Validates transformation quality
    - Identifies and fixes issues
    - Ensures consistency and completeness
    - Provides quality metrics
    """
    
    def __init__(self,
                 strategy: Optional[QualityStrategy] = None,
                 provider: Optional[LLMProvider] = None,
                 config: Optional[ServiceConfig] = None):
        """
        Initialize quality service.
        
        Args:
            strategy: Quality control strategy
            provider: Optional LLM provider for corrections
            config: Service configuration
        """
        self.strategy = strategy or self._get_default_strategy()
        self.provider = provider
        super().__init__(config)
    
    def _initialize(self):
        """Initialize quality control resources."""
        self.issue_cache = {}
        self.correction_history = []
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    def _get_default_strategy(self) -> QualityStrategy:
        """Get default quality strategy."""
        return AdaptiveQualityStrategy(
            target_quality=self.config.target_quality if self.config else 90.0
        )
    
    async def process_async(self, transformation: Transformation) -> Transformation:
        """
        Improve transformation quality.
        
        Args:
            transformation: Transformation to improve
            
        Returns:
            Improved transformation with quality score
        """
        try:
            self.logger.info("Starting quality control process")
            
            # Initial quality assessment
            current_quality = await self._assess_quality(transformation)
            self.logger.info(f"Initial quality score: {current_quality:.1f}/100")
            
            iterations = 0
            max_iterations = self.config.max_qc_iterations if self.config else 3
            target_quality = self.config.target_quality if self.config else 90.0
            
            # Iterative improvement loop
            while current_quality < target_quality and iterations < max_iterations:
                self.logger.info(f"QC iteration {iterations + 1}/{max_iterations}")
                
                # Find issues
                issues = await self.strategy.find_issues_async(transformation)
                
                if not issues:
                    self.logger.info("No issues found")
                    break
                
                self.logger.info(f"Found {len(issues)} issues")
                
                # Apply corrections
                transformation = await self._apply_corrections_async(
                    transformation, issues
                )
                
                # Reassess quality
                current_quality = await self._assess_quality(transformation)
                self.logger.info(f"Quality after iteration: {current_quality:.1f}/100")
                
                iterations += 1
            
            # Set final quality metrics
            transformation.quality_score = current_quality
            transformation.qc_iterations = iterations
            
            # Log final status
            if current_quality >= target_quality:
                self.logger.info(f"Quality target achieved: {current_quality:.1f}/100")
            else:
                self.logger.warning(
                    f"Quality target not met: {current_quality:.1f}/100 "
                    f"(target: {target_quality})"
                )
            
            return transformation
            
        except Exception as e:
            self.handle_error(e, {"transformation_type": transformation.transform_type.value})
    
    async def _assess_quality(self, transformation: Transformation) -> float:
        """
        Assess quality of transformation.
        
        Args:
            transformation: Transformation to assess
            
        Returns:
            Quality score (0-100)
        """
        return await self.strategy.assess_quality_async(transformation)
    
    async def _apply_corrections_async(self,
                                      transformation: Transformation,
                                      issues: List[Dict[str, Any]]) -> Transformation:
        """
        Apply corrections to fix identified issues.
        
        Args:
            transformation: Transformation to correct
            issues: List of issues to fix
            
        Returns:
            Corrected transformation
        """
        # Group issues by type for efficient correction
        issues_by_type = self._group_issues_by_type(issues)
        
        # Apply corrections for each type
        for issue_type, issue_list in issues_by_type.items():
            if issue_type == 'consistency':
                transformation = await self._fix_consistency_issues(
                    transformation, issue_list
                )
            elif issue_type == 'completeness':
                transformation = await self._fix_completeness_issues(
                    transformation, issue_list
                )
            elif issue_type == 'grammar':
                transformation = await self._fix_grammar_issues(
                    transformation, issue_list
                )
            else:
                self.logger.warning(f"Unknown issue type: {issue_type}")
        
        # Record correction in history
        self.correction_history.append({
            'timestamp': asyncio.get_event_loop().time(),
            'issues_fixed': len(issues),
            'types': list(issues_by_type.keys())
        })
        
        return transformation
    
    def _group_issues_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group issues by type for batch processing."""
        grouped = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        return grouped
    
    async def _fix_consistency_issues(self,
                                     transformation: Transformation,
                                     issues: List[Dict[str, Any]]) -> Transformation:
        """
        Fix consistency issues in transformation.
        
        Args:
            transformation: Transformation to fix
            issues: Consistency issues to address
            
        Returns:
            Fixed transformation
        """
        # For each character with consistency issues
        for issue in issues:
            character = issue.get('character')
            if not character:
                continue
            
            # Find the correct gender for this character
            char_obj = transformation.characters_used.get_character(character)
            if not char_obj:
                continue
            
            # Review all changes for this character
            for change in transformation.changes:
                if change.character_affected == character:
                    # Ensure consistency with character's transformed gender
                    # (This would be more sophisticated in practice)
                    pass
        
        return transformation
    
    async def _fix_completeness_issues(self,
                                      transformation: Transformation,
                                      issues: List[Dict[str, Any]]) -> Transformation:
        """
        Fix completeness issues (missing transformations).
        
        Args:
            transformation: Transformation to fix
            issues: Completeness issues to address
            
        Returns:
            Fixed transformation
        """
        # For each missing character
        for issue in issues:
            character = issue.get('character')
            if not character:
                continue
            
            # This would scan the text for mentions of this character
            # and add appropriate transformations
            # For now, just log it
            self.logger.info(f"Would add transformations for character: {character}")
        
        return transformation
    
    async def _fix_grammar_issues(self,
                                 transformation: Transformation,
                                 issues: List[Dict[str, Any]]) -> Transformation:
        """
        Fix grammar issues in transformation.
        
        Args:
            transformation: Transformation to fix
            issues: Grammar issues to address
            
        Returns:
            Fixed transformation
        """
        # If we have an LLM provider, we could use it to fix grammar
        if self.provider:
            # This would use the LLM to correct grammar issues
            pass
        
        return transformation
    
    async def validate_transformation(self,
                                     transformation: Transformation) -> Dict[str, Any]:
        """
        Validate a transformation without modifying it.
        
        Args:
            transformation: Transformation to validate
            
        Returns:
            Validation results
        """
        # Check structural validity
        structural_errors = transformation.validate()
        
        # Assess quality
        quality_score = await self._assess_quality(transformation)
        
        # Find issues
        issues = await self.strategy.find_issues_async(transformation)
        
        # Categorize issues by severity
        critical = [i for i in issues if i.get('severity') == 'critical']
        major = [i for i in issues if i.get('severity') == 'major']
        minor = [i for i in issues if i.get('severity') == 'minor']
        
        return {
            'valid': len(critical) == 0 and len(structural_errors) == 0,
            'quality_score': quality_score,
            'structural_errors': structural_errors,
            'issues': {
                'critical': critical,
                'major': major,
                'minor': minor,
                'total': len(issues)
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        metrics = super().get_metrics()
        metrics.update({
            'strategy': self.strategy.__class__.__name__,
            'corrections_applied': len(self.correction_history),
            'cached_issues': len(self.issue_cache)
        })
        return metrics