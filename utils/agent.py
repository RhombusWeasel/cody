from utils.tool import get_tools
from utils.cfg_man import cfg, register_default_config
from utils.skills import skill_manager
from utils.providers import get_provider, get_provider_config

class Agent():
    def __init__(self):
        system_prompt = cfg.get("prompts.system", "")
        wd = cfg.get("session.working_directory", "")
        if system_prompt:
            system_prompt = system_prompt.replace("{working_directory}", str(wd))
            
        skills_xml = skill_manager.get_catalog_xml()
        if skills_xml:
            skills_instructions = (
                "The following skills provide specialized instructions for specific tasks.\n\n"
                "When a task matches a skill's description, call the activate_skill tool with the skill's name to load its full instructions.\n\n",
                "This is the most important task, the skill data is user configured and contains details about what is required of you to use the skills and any standards etc that the user would prefer.  Always activate the skill before calling run_skill.\n\n"
                "You should always favour skills over general system commands as they provide additional safeguards against errors and are user configured so should conform to any required compliance rules in place."
            )
            system_prompt += f"\n\n{skills_instructions}\n\n```xml\n{skills_xml}\n```"
            
        self.msg = [
            {'role': 'system', 'content': system_prompt}
        ]
        # Cumulative token usage for the current chat session
        self.total_usage = None

    def add_msg(self, role: str, msg: str, **kwargs):
        self.msg.append({
            'role': role,
            'content': msg,
            **kwargs
        })

    def get_response(self, msg: str, role: str='user'):
        tools = get_tools(['skills', 'system'])
        if msg != "":
            self.add_msg(role, msg)
        _, model, opts = get_provider_config()
        provider = get_provider()
        resp = provider.chat(
            model=model,
            messages=self.msg,
            tools=tools if tools else None,
            options=opts,
        )
        if resp.message.content or resp.message.tool_calls:
            kwargs = {}
            if resp.message.tool_calls:
                kwargs['tool_calls'] = resp.message.tool_calls
            if resp.message.thoughts:
                kwargs['thoughts'] = resp.message.thoughts
            self.add_msg('assistant', resp.message.content or "", **kwargs)
        # Accumulate token usage — only track prompt tokens (what we send back to the model)
        if resp.usage:
            if self.total_usage is None:
                from utils.providers.base import TokenUsage
                self.total_usage = TokenUsage(
                    context_window=resp.usage.context_window,
                )
            self.total_usage.prompt_tokens = resp.usage.prompt_tokens
        return resp

    def get_response_stream(self, msg: str, role: str='user'):
        """Stream a response, yielding (content_delta, thoughts_delta) tuples.
        Accumulates the full response in self.msg at the end.
        """
        from utils.providers.base import StreamChunk
        tools = get_tools(['skills', 'system'])
        if msg != "":
            self.add_msg(role, msg)
        _, model, opts = get_provider_config()
        provider = get_provider()

        full_content = ""
        full_thoughts = ""
        chunks = provider.stream_chat(
            model=model,
            messages=self.msg,
            tools=tools if tools else None,
            options=opts,
        )
        for chunk in chunks:
            full_content += chunk.content
            if chunk.thoughts:
                full_thoughts += chunk.thoughts
            yield chunk.content, chunk.thoughts

            if chunk.done:
                kwargs = {}
                if full_content or full_thoughts:
                    if full_thoughts:
                        kwargs['thoughts'] = full_thoughts
                    self.add_msg('assistant', full_content, **kwargs)
                # Accumulate token usage — only track prompt tokens (what we send back to the model)
                if chunk.usage:
                    if self.total_usage is None:
                        from utils.providers.base import TokenUsage
                        self.total_usage = TokenUsage(
                            context_window=chunk.usage.context_window,
                        )
                    self.total_usage.prompt_tokens = chunk.usage.prompt_tokens

class TaskAgent():
    """A simple agent workflow that can be passed specific tools to affect application state."""
    def __init__(self, system_prompt: str, tools: list = None):
        self.msg = [{'role': 'system', 'content': system_prompt}]
        self.tools = tools or []
        self.tool_map = {t.__name__: t for t in self.tools}

    def add_msg(self, role: str, msg: str, **kwargs):
        self.msg.append({'role': role, 'content': msg, **kwargs})

    async def run(self, user_msg: str):
        import asyncio
        import json
        if user_msg:
            self.add_msg('user', user_msg)
        _, model, opts = get_provider_config()
        provider = get_provider()
        while True:
            resp = await asyncio.to_thread(
                provider.chat,
                model=model,
                messages=self.msg,
                tools=self.tools if self.tools else None,
                options=opts,
            )
            
            if resp.message.content or resp.message.tool_calls:
                msg_kwargs = {}
                if resp.message.tool_calls:
                    msg_kwargs['tool_calls'] = resp.message.tool_calls
                self.add_msg('assistant', resp.message.content or "", **msg_kwargs)
                
            if not resp.message.tool_calls:
                return resp.message.content
                
            for tool_call in resp.message.tool_calls:
                func_name = tool_call.function.name
                args = tool_call.function.arguments or {}
                if isinstance(args, str):
                    args = json.loads(args) if args else {}
                if func_name in self.tool_map:
                    func = self.tool_map[func_name]
                    try:
                        if asyncio.iscoroutinefunction(func):
                            result = await func(**args)
                        else:
                            result = func(**args)
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = f"Unknown tool: {func_name}"
                    
                if not isinstance(result, str):
                    result = json.dumps(result)
                    
                tool_data = json.dumps({
                    'function': func_name,
                    'arguments': args,
                    'result': result
                })
                self.add_msg('tool', tool_data)

register_default_config({
  "prompts": {
    "system": (
      "\nYou are Cody a highly skilled programming assistant.\n\n"
      "You are currently working in the directory: {working_directory}\n"
    ),
  },
})
