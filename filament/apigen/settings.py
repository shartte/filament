value_types = {
    "filament::Box",
    "filament::Frustum",
    "filament::driver::BufferDescriptor",
    "filament::driver::PixelBufferDescriptor",
    "utils::Entity"
}

# This superclass marks a class something that cannot be constructed or destructed by the client
# as such references to these objects are always borrowed and never owned
borrowed_obj_superclass = "filament::FilamentAPI"
builder_superclass = "filament::BuilderBase<T>"

public_apis = {
    "utils::EntityManager",
    "filament::Camera",
    "filament::Color",
    "filament::DebugRegistry",
    "filament::Fence",
    "filament::SwapChain",
    "filament::Engine",
    "filament::IndexBuffer",
    "filament::IndexBuffer::Builder",
    "filament::IndirectLight",
    "filament::IndirectLight::Builder",
    "filament::LightManager",
    "filament::LightManager::Builder",
    "filament::TextureSampler",
    "filament::MaterialInstance",
    "filament::Texture",
    "filament::Texture::Builder",
    "filament::Material",
    "filament::Material::Builder",
    "filament::VertexBuffer",
    "filament::VertexBuffer::Builder",
    "filament::Renderer",
    "filament::RenderableManager",
    "filament::RenderableManager::Builder",
    "filament::Scene",
    "filament::Skybox",
    "filament::Skybox::Builder",
    "filament::Stream",
    "filament::Stream::Builder",
    "filament::TransformManager",
    "filament::Viewport",
    "filament::View"
}
