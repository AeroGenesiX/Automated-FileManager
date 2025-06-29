import abc

class AbstractLLMSkill(abc.ABC):
	@abc.abstractmethod
	def skill_name(self) -> str:
		raise NotImplementedError("Subclasses must implement skill_name()")

	@abc.abstractmethod
	def can_handle(self, natural_language_input: str, context: dict) -> bool:
		"""
		Check if this skill can handle the given input and context.
		Context might include current_path, selected_files, etc.
		"""
		raise NotImplementedError("Subclasses must implement can_handle()")

	@abc.abstractmethod
	def execute(self, natural_language_input: str, context: dict, llm_service) -> tuple[bool, str]:
		"""
		Execute the skill.
		Returns (success_boolean, message_or_result_string)
		Might use llm_service for further LLM calls if needed.
		"""
		raise NotImplementedError("Subclasses must implement execute()")