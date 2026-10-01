# A Blender-style 3D studio in chat: the agent builds the scene, the user moves
# things by hand in the Studio app, real Blender renders it.
#
#   uv run cycls run examples/studio.py      # localhost:8080
#
# Needs the Blender engine deployment (cycls-render, see engine/README.md) and,
# in .providers.env: ANTHROPIC_API_KEY, CYCLS_STUDIO_ENGINE=cycls-render and
# CYCLS_API_KEY (cycls.remote calls the engine with it).
import cycls
import cycls_studio

llm = (
    cycls.LLM()
    .model("anthropic/claude-sonnet-5")
    .system("You are a 3D artist working in the Studio with the user. Build what they describe, "
            "keep it tasteful and well lit, and explain briefly what you did.")
    .allowed_tools(["Canvas"])
)


@cycls.agent(
    image=cycls.Image().pip("cycls-studio").copy(".providers.env", ".env"),
    web=cycls.Web().auth(cycls.Clerk()).title("Studio").use(cycls_studio.Studio()),
    volumes={"/workspace": cycls.Volume("studio-agent")},
)
async def studio(context):
    async for ev in llm.run(context=context):
        yield ev
